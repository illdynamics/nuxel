# 07 — TOUCHSCREEN, END TO END (P3 / mission §11–§12)

## 11.1–11.3 The stages, each one measured this cycle

| # | Stage | State | Evidence (live handset) |
|---|---|---|---|
| 1 | normal boot, not charger mode | **PASS** | `tr ' ' '\n' < /proc/cmdline \| grep -c androidboot.mode=charger` → `0` |
| 2 | `sec_touchscreen` registered | **PASS** | `/proc/interrupts` → `431: 60 … sec_ts`; `/sys/class/sec/tsp/` present (incl. `all_touch_count`) |
| 3 | IRQ counter moves on touch | **PASS (previous cycle, re-armed this cycle)** | A29b: `sec_ts 16→225`, `304→565`, `[P] tID:0.0 z:63 …`, `[R] … dd:20,-2`; this cycle the counter read 57→60 and `nuxel-touch-arm.state` holds `TOUCH_POINT slot=0 n=41` |
| 4 | evdev delivers events | **PASS** | `nuxel-touch-arm` holds `/dev/input/event2` and logs `TOUCH_POINT slot=<n> n=<count>` |
| 5 | libinput receives them | **FIXED this cycle** | shim log: `PATH_ADD node=/dev/input/event2 name='sec_touchscreen' accepted=1` |
| 6 | compositor owns the device | **FIXED this cycle** | `ls -l /proc/<phoc>/fd` → `24 -> /dev/input/event2`, `25 -> /dev/input/event4` (was **0** input fds) |
| 7 | Phoc delivers Wayland events to the view | **FIXED this cycle** (device now present in the seat; single fullscreen toplevel) | phoc ran with `WLR_BACKENDS=headless,libinput` + an active-enough libseat session |
| 8 | WebKit → PWA DOM | **instrumented this cycle** | injected observer reports the real document's events into `/run/nuxel-home.state` (see below) |
| 9 | PWA activation callback | **instrumented** | the same observer also reports `app:launch` (dispatched by `js/apps.js launchApp()`) |

## The actual defect (stage 5/6) and why it took 6 cycles

`nuxel-wayland.service` started phoc with **`WLR_BACKENDS=headless`**. In wlroots
0.19.3 the backend list is taken literally (`backend/backend.c::attempt_backend_by_name`),
so the `libinput` backend was never even attempted — the compositor opened
**zero** input devices and no finger could ever reach a client, while every layer
below it (sec_ts, evdev, userspace reader) was working. Requesting libinput then
failed at the *next* step:

```
phoc-wlroots-CRITICAL [backend/backend.c:305] failed to start a session
phoc-wlroots-CRITICAL [backend/backend.c:355] failed to add backend 'libinput'
```

wlroots only creates the libinput backend when a backend **session** exists, and
this handset cannot provide one the usual way:

* **no VT at all** — `/dev/tty0` absent, `/sys/class/vtconsole` absent,
  `/proc/consoles` empty → seatd's VT-bound seat can never activate
  (measured: `[backend/backend.c:105] Timeout waiting session to become active`);
* **libseat on Fedora 43 has only `logind`/`seatd`/`noop`** (the `builtin` backend
  is not built; verified by scanning `libseat.so.1`), and there is no logind
  session on this image;
* **systemd-udevd is masked** by design (`tools/s10plus/a26/nuxel-rootfs-fixes.sh`):
  it cannot register worker objects on Linux 4.14 (`Failed to create worker object:
  Function not implemented`) and forks unboundedly. Re-enabling it in this cycle
  reproduced the storm: process count 281 → 544 within seconds of
  `udevadm trigger --subsystem-match=input` (then killed, back to 281 in 3 s).

So the input path was completed with the smallest possible, auditable substitute
(`tools/s10plus/a31/nuxel-libinput-path.c`, an `LD_PRELOAD` shim, 70 KB):

1. `libseat_open_seat` via **`LIBSEAT_BACKEND=noop`** satisfies wlroots' session
   requirement (measured: the session timeout disappears);
2. the shim interposes `libinput_udev_create_context` → `libinput_path_create_context`
   and `libinput_udev_assign_seat` → `libinput_path_add_device` for the
   `/dev/input/eventN` nodes whose **capability** (INPUT_PROP_DIRECT) proves they
   are the panel — never by event number;
3. libinput 1.30's path backend still resolves the node to a udev device
   (`src/path-seat.c`: `udev_device_new_from_devnum` + a 200 × 10 ms wait for the
   `I:` initialized marker) which can never appear without udevd, so the shim
   writes that single database entry (`/run/udev/data/c13:66`) **from the device's
   own capabilities** before handing the node to libinput;
4. a scoped `libseat_open_device`/`libseat_close_device` fallback for
   `/dev/input/` paths exists as a safety net (measured **not needed**: libseat's
   noop backend returned device id 24/25 and the opens succeeded —
   `DEVICE_OPEN_LIBSEAT path=/dev/input/event2 rc=24`).

**No synthetic events are produced anywhere in this chain.** The kernel evdev
node is opened, libinput parses the real multitouch protocol, wlroots creates a
`wl_touch`, the compositor delivers it to the WebKit view.

## §12 — proving the last two stages (a single physical tap)

The A31 host injects a read-only observer (a WebKit user script) into the *real*
launcher document. It does not touch `pwa/nuxel-home/`; it reports, for each
event the document receives: kind, viewport coordinates, the element/id it hit,
viewport size, `devicePixelRatio`, and whether `#boot-splash` is still in the DOM.
It also reports `app:launch`, the event `js/apps.js launchApp()` dispatches when
an app tile is activated. Everything lands in `/run/nuxel-home.state`:

```
NUXEL_INPUT EVT touchstart x=… y=… tag=… id=… w=… h=… dpr=… splash=absent
NUXEL_INPUT EVT app:launch id=org.nuxel.Notes name=Notes
```

Correlated with `grep -w sec_ts /proc/interrupts` and
`/run/nuxel-touch-arm.state` for the same window, one finger can be followed
through every layer. **The physical tap itself is the user's to perform** — the
software side is instrumented and waiting (doc 10 records the measured result).

## Coordinate mapping (§13)

* Wayland output: `[output:HEADLESS-1] mode = 720x1520 scale = 2` → 360×760 CSS
  px, the same band the VM renders (`720x1440 @ scale 2`).
* Panel: 1440×3040 fbdev; the bridge blits 720×1520 → 1440×3040 by integer scale,
  and reports `out=720x1520 src=720x1520 scale=2 panel=1440x3040`.
* Touch: raw range `x=[0..4095] y=[0..4095]`, mapped by libinput/wlroots to the
  compositor's output — the compositor, not the bridge, owns input mapping, so
  graphics and input cannot disagree.
* The observer reports the viewport (`w`, `h`) and `devicePixelRatio` the page
  actually sees, so any mismatch is visible from the log instead of guessed.
