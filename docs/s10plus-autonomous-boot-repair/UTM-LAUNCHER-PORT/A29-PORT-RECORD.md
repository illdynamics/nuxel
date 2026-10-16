# A29 — PORT OF THE EXISTING UTM LAUNCHER TO THE GALAXY S10+ (live engineering record)

**Directive honoured:** no new launcher, no redesign, no image analysis. The
launcher that already runs in the UTM VM was located in source and re-verified on
the *live* VM this cycle, and that same implementation is what the S10+ port
targets. Touch was diagnosed to kernel-driver level with measured evidence.

Everything below is either (a) source in this repository, (b) output of a command
run against the live VM/handset, or (c) explicitly marked as *not verified*.

---

## 1. What the UTM launcher actually is (re-verified live this cycle)

| Question | Answer | Evidence (live, this cycle) |
|---|---|---|
| Exact executable | The **Nuxel Home PWA** `pwa/nuxel-home/` rendered by **WebKitGTK**, served by the VM's static server on `127.0.0.1:8000` | `services/nuxel-web.service`: *"Nuxel PWA Static Web Server (nuxel-home launcher on :8000)"*; guest `python3 -m http.server 8000 --bind 127.0.0.1` (pid 878) |
| Which process/session | Phosh session on Wayland: `gdm-wayland-session --register-session phosh-session` → `phoc -v -S -C /usr/share/phosh/phoc.ini -E gnome-session --session=phosh` → `libexec/phosh` | `ps` on the running guest |
| Which service starts it | `nuxel-web.service` (server) + the session; the browser host is started in-session | `systemctl list-units` on the guest |
| Source directory | `pwa/nuxel-home/` (`index.html`, `css/{style,launcher,search,status-bar}.css`, `js/{app,apps,launcher,search,recents,status-bar,qs,bridge}.js`, `icons/`, `assets/`) | repository + guest `/usr/share/nuxel/nuxel-home` |
| Engine / libraries | WebKitGTK (guest has `webkit2gtk4.1-2.52.5-1.fc43`, `webkitgtk6.0`, `gtk3-3.24.52`) | `rpm -q` on the guest |
| Application registry | `pwa/nuxel-home/js/apps.js` (`NUXEL_APPS`), 9 apps / 3 docked; tapping a tile runs `appRegistry.launchApp()` → `js/app.js _openPwa()` opens the registry `url` as a **fullscreen iframe** | source |
| Native GTK twin | `shell/nuxel-home-native/` is **installed but broken** in the VM: `/usr/local/bin/nuxel-home` → `ImportError: attempted relative import with no known parent package`; `nuxel-home-native.service` and `nuxel-home-kiosk.service` are `disabled` | ran it live on the guest, twice, same traceback |
| VM display geometry | `[output:Virtual-1] mode = 720x1440 scale = 2` → **360 CSS px** viewport (the `@media (max-width:480px)` band) | guest `/usr/share/phosh/phoc.ini` |

**Correction to the A28 record:** A28 states the phone image contains *no browser
engine* and that Option B was unavailable. Both are wrong. The handset image
contains `webkit2gtk4.1-2.52.5-1.fc43`, `webkitgtk6.0-2.52.5-1.fc43`,
`gtk3-3.24.52-1.fc43`, `gtk4-4.20.4`, `mesa-*`, `wlroots-0.19.3`,
`phosh-0.54.0`, `phoc`, `gnome-session` and `wayland-sessions/phosh.desktop`
(measured with `rpm -qa` on the live handset). Only the *output device* was
missing.

---

## 2. The handset's actual graphics constraint (measured, not assumed)

```
handset:  uname -r = 4.14.253   /proc/fb = 0,1   ls /dev/dri -> missing
          /sys/class/drm -> empty
          /proc/config.gz:  # CONFIG_DRM is not set
                            CONFIG_FB=y  CONFIG_ION=y  CONFIG_MALI_MIDGARD=y
```

No DRM ⇒ no KMS/GBM/EGL output ⇒ no wlroots-DRM, no weston-DRM, no
`Egl`/`Gbm` Wayland client path, and `phoc`/`gnome-session` cannot take the panel
by themselves. The phone also has **no Xorg** and **no weston/sway/cage** (`which`
on the handset), so the X path was not used either.

**What does work (measured live this cycle):**

```
WLR_BACKENDS=headless WLR_RENDERER=pixman phoc --no-xwayland -C /usr/share/phosh/phoc.ini
  -> "Linux dmabuf support unavailable"
  -> "Running compositor on wayland display 'wayland-0'"
  -> "Output 'HEADLESS-1' added"
  -> /run/phoc-test/wayland-0 exists
```

wlroots 0.19 (the version in the image) still ships the **headless** backend and
the **pixman** renderer, so a stock Wayland compositor runs on this kernel with a
virtual output whose geometry comes from `phoc.ini`
(`[output:HEADLESS-1] mode = 720x1440 scale = 2`). That is the port's foundation:
**Wayland-only, no Xorg, no DRM.**

---

## 3. Architecture of the port (all stock components + one transport adapter)

```
Samsung bootloader -> Nuxel boot animation (fb) -> Fedora systemd
   |
   +-- nuxel-touch-arm.service    arm the sec_ts controller (see section 4)
   +-- nuxel-wayland.service      phoc (WLR_BACKENDS=headless, WLR_RENDERER=pixman)
   |        `- nuxel-session.sh   python3 -m http.server 8000 --bind 127.0.0.1
   |                             (docroot /usr/share/nuxel = the VM's nuxel-web)
   |            `- nuxel-pwa-host  WebKitGTK view of the SAME launcher PWA
   +-- nuxel-wl-fb.service        WAYLAND screencopy -> /dev/fb0 (the only adapter)
   +-- nuxel-fallback.service     runs /usr/bin/nuxel-ui (the A27 fb UI) ONLY if
                                  /run/nuxel-launcher-ready was never written
```

* Nothing in `pwa/nuxel-home/` is modified, copied into C, or re-styled. The
  launcher's own CSS/JS/icons/registry are what the phone renders.
* Applications are launched by the launcher's own `js/app.js` iframe path, so the
  app registry stays single-sourced.
* The only new display code is `nuxel-wl-fb.c`: it takes composited frames through
  `zwlr_screencopy_manager_v1` (shm - no DMABUF is available on this kernel) and
  writes them to the AMOLED through `/dev/fb0` (integer scale 720x1520 → 1440x3040).
* Fallback semantics: `nuxel-fallback.service` uses
  `ExecCondition=/usr/lib/nuxel/nuxel-launcher-ready-wait 60`, which exits 0 only
  when the launcher never became ready. Two framebuffer owners can therefore
  never run at the same time.

Sources (this cycle, all committed under `tools/s10plus/a29/`):
`nuxel-touch-arm.c`, `nuxel-wl-fb.c`, `nuxel-pwa-host.c`,
`wlr-screencopy-unstable-v1.xml`, `phoc-phone.ini`, `nuxel-session.sh`,
`nuxel-wait-wayland`, `nuxel-launcher-ready-wait.sh`, the four unit files,
`build-a29-vm.sh` (build), `push-file.sh` (transport).

Build channel: the **live UTM VM** (`nuxel@192.168.64.3`), Fedora 43 aarch64 with
the same `webkit2gtk4.1-2.52.5` / `gtk3-3.24.52` the handset carries, so ELF
dependencies match by construction. The podman cross-build path was abandoned:
on this host the podman machine's gvproxy API socket is unstable
(`unable to connect to "gvproxy" socket`).

---

## 4. P0 — THE TOUCHSCREEN: root causes found on hardware

### Root cause 1 — the touchscreen node was never opened (userspace)

`/dev/input` enumerates **descending** (`event10, event9, … event3`) and
`tools/s10plus/nuxel-ui.c input_scan()` stops after `NIN < 8` devices. The panel
node is `event2` (`sec_touchscreen`), so it was *never scanned*; every A23–A28
build only ever saw `event3 sec_touchpad` (`direct=0`), which carries no touch
points. Evidence — the handset's own log:

```
INPUT_DEVICE path=/dev/input/event9 name='hall'
...
INPUT_DEVICE path=/dev/input/event3 name='sec_touchpad'
INPUT_CAPS abs+mt=1
INPUT_CAPS direct=0 btn_touch=1 slots=10 x=[0.4095] y=[0.4095]
TOUCH_DEVICE_LOST re-scanning /dev/input        <-- every ~10 ms
```
and `ls -l /proc/<nuxel-ui>/fd` showed fds for `event4..7` only — never
`event2`/`event3`.

The correct device, identified by capability (never by event number), is:

```
ARMED_OK path=/dev/input/event2 name='sec_touchscreen'
        mt=1 direct=1 btn=1 slots=10 x=[0.4095] y=[0.4095]
```

### Root cause 2 — the driver never enables the touch IRQ (kernel)

`drivers/input/touchscreen/sec_ts/y771/sec_ts.c` (Linux4 tree, commit
`f7194c1d`): `probe()` ends with `ts->power_status = SEC_TS_STATE_POWER_ON;`, and

```c
int sec_ts_start_device(struct sec_ts_data *ts) {
        int ret = -1;
        ...
        if (ts->power_status == SEC_TS_STATE_POWER_ON) {
                input_err(true, ..., "%s: already power on\n", __func__);
                goto out;                       /* returns -1 */
        }
        ...
        enable_irq(ts->client->irq);            /* NEVER REACHED */
}
static int sec_ts_input_open(struct input_dev *dev) {   /* still returns 0 */
        else { ret = sec_ts_start_device(ts);
               if (ret < 0) input_err(..., "Failed to start device\n"); }
        ...
        return 0; }
```

Measured on the handset, repeating every ~2 s (the display notifier re-opens the
device):

```
sec_ts 4-0048: sec_ts_input_open: Failed to start device
sec_ts 4-0048: sec_ts_start_device: already power on
```

Consequences: **`open()` on the panel node always succeeds and always silently
does nothing** — no `SENSE_ON`, no `enable_irq()`. This is why no finger was ever
captured in A23–A28 (the 900 s capture stayed 0 bytes) and why the raw
`open → close → open` re-arm used by `nuxel-touch-arm` does not help: 400 s of
kernel log contain **zero `sec_ts_stop_device` lines**, so `power_status` never
leaves `POWER_ON`.

### The lever that does work (driver's own factory commands)

`sec_ts_fn.c` exposes the stop/start pair on `/sys/class/sec/tsp/cmd`:

```c
static void module_off_master(...) { ret = sec_ts_stop_device(ts); ... }  /* disable_irq + POWER_OFF */
static void module_on_master (...){ ret = sec_ts_start_device(ts); ... }  /* power on + SENSE_ON + enable_irq */
```

Measured on the handset:

```
$ echo module_off_master > /sys/class/sec/tsp/cmd
$ cat /sys/class/sec/tsp/cmd_result
module_off_master:OK
$ grep -w sec_ts /proc/interrupts
431:  61  ...  exynos7_wkup_irq_chip 0 Level  sec_ts      # static since boot
... after the stop + the next open (real start path):
431:  63  ...  exynos7_wkup_irq_chip 0 Level  sec_ts      # first movement ever
```
and the driver began reading events from the IC for the first time
(`sec_ts_read_event: STATUS 1d 61 2 2 3 0 0 0`, `Normal changed`,
`sec_ts_get_touch_function: touch_functions:61 ic_status:61`).

`module_on_master` returns `NG` / `write error: Device or resource busy` while the
2 s notifier storm holds the command engine, but the `module_off_master` stop
followed by *any* `sec_ts_input_open()` (the notifier's own next call) already
runs the real start and enables the IRQ — that is the armed state the port uses.
`nuxel-touch-arm.c` now issues `module_off_master` → `open()` →
`module_on_master` (best effort) → **holds the fd open for the session** so the
armed state survives, and logs every contact to `/run/nuxel-touch-arm.state`.

### Verified / not verified (honest)

| Item | State |
|---|---|
| Panel node identified by capability (`event2`, MT, DIRECT, 10 slots, 0..4095) | **VERIFIED** on the handset |
| Driver short-circuit understood and reproduced in the kernel log | **VERIFIED** |
| `module_off_master` runs `sec_ts_stop_device()` and the sec_ts IRQ counter moves (61→63) | **VERIFIED** |
| `nuxel-touch-arm` deployed (sha256 `0936e4ddbc305fe4b1b038be3f8bf5fdc3bfabb29d71a1dbef0d645bfe0f252e`) and active | **VERIFIED** |
| A finger producing `TOUCH_POINT` / a rising sec_ts IRQ counter | **NOT YET VERIFIED** — two tap windows (75 s, 55 s) produced `delta=0`; the handset was being driven in a live session and it is not established whether the glass was touched inside those windows |

---

## 5. Deployment record (live, no flash, no TWRP)

Transport reality (measured): this console silently drops command lines longer
than ~512 characters — 256 and 512 landed byte-exact, 768/1024/1536/2048 arrived
empty. The existing `nuxel-live-deploy.sh` framing never produced an end marker on
this handset (three attempts, `TRANSPORT MISMATCH`, nothing installed), so A29
added `tools/s10plus/a29/push-file.sh`: gzip + base64, 380-character chunks, and
**every chunk acknowledged by reading the cumulative file length back from the
target** (never the command echo). Final step gunzips, compares SHA-256, installs
atomically and re-reads the installed path.

Installed on the handset (each SHA-256-verified on the target):

| Path | sha256 (first 16) |
|---|---|
| `/usr/lib/nuxel/nuxel-touch-arm` | `0936e4ddbc305fe4` |
| `/usr/lib/nuxel/nuxel-wl-fb` | `c1c468ae79f860be` |
| `/usr/lib/nuxel/nuxel-pwa-host` | `cfc9d8206052bd12` |
| `/usr/lib/nuxel/nuxel-session.sh` | `b5e8874ae4d6776c` |
| `/usr/lib/nuxel/nuxel-wait-wayland` | `138542d1e6123858` |
| `/usr/lib/nuxel/nuxel-launcher-ready-wait` | `f69c0be91eb343a5` |
| `/etc/nuxel/phoc-phone.ini` | `c91f0505f1b2f7ad` |
| `/etc/systemd/system/nuxel-{touch-arm,wayland,wl-fb,fallback}.service` | `ba7f1388…`, `e7610a63…`, `68330709…`, `9f410a19…` |

`daemon-reload` was run; `nuxel-touch-arm.service` is **active**. The launcher
units are installed but **not enabled** — the A27 framebuffer UI still owns the
panel, so the phone is exactly as it was before, plus the arming helper.

Console note: the handset's kmsg mirror (`/opt/nuxel/nuxel-console`, pid 3526)
was SIGSTOPped during this cycle to make the link usable and must be resumed with
`kill -CONT <pid>`.

---

## 6. Remaining steps (exact, in order)

1. **Close the finger test.** Open a capture window and tap during it:
   `nuxel-live.sh --run 'a=$(grep -w sec_ts /proc/interrupts|awk "{print \$2}"); sleep 55; b=$(grep -w sec_ts /proc/interrupts|awk "{print \$2}"); echo delta=$((b-a)); cat /run/nuxel-touch-arm.state'`
   A rising counter plus `TOUCH_POINT slot=…` closes P0. If the counter still does
   not move, the next lever is re-issuing `module_off_master` immediately before
   the tap window (the arm is stateful and the notifier storm flips it back).
2. **Bring the launcher up live** (scan does not touch the panel until step 3):
   `systemctl start nuxel-wayland && systemctl start nuxel-wl-fb` — expect
   `/run/nuxel-wl-fb.state` to read `FB_OPEN_OK … 1440x3040` and then
   `FRAMES_OK`, and `/run/nuxel-home.state` to read `NUXEL_HOME_READY`.
3. **Cross over:** `systemctl stop nuxel-ui` (the bridge already owns `/dev/fb0`,
   so the AMOLED stays lit), then `systemctl enable nuxel-wayland nuxel-wl-fb
   nuxel-fallback` and `systemctl disable nuxel-ui`.
4. Only if the launcher does not become ready does `nuxel-fallback.service` start
   the A27 UI; both are never running together.
5. Add the A29 files + units to `images/s10plus/build-phone-rootfs-inside-fedora.sh`
   so a fresh image ships them (the live session only proved the deployment).

## 7. Known limitations (unchanged by this cycle)

* No DRM ⇒ no hardware EGL/GBM ⇒ WebKit renders in software
  (`WEBKIT_DISABLE_COMPOSITING_MODE=1`) and the bridge performs a CPU blit to the
  AMOLED. Frame rate has not been measured yet.
* Telephony/SMS/camera/audio paths are not claimed; only what the register shows.
* A kernel with `CONFIG_DRM=y` + exynos/decon support would remove the bridge
  entirely and let `phosh` run as in the VM; that is a separate, deliberately
  un-rushed kernel project (boot-partition write required).

---

## 8. A29b — live verification cycle (2026-09-15/16, handset on USB)

All of the following was measured on the running handset this cycle; nothing here
is inferred. Console: `/dev/cu.usbmodem201`, transport `nuxel-live.sh` (framed,
SHA-verified) + `tools/s10plus/a29/push-file.sh` for files.

### 8.1 Boot mode is a hard prerequisite for touch (root cause of "no finger for 6 cycles")

The handset had booted in **charger mode**:

```
/proc/cmdline: androidboot.mode=charger   charging_mode=0x3030
dmesg:         tsp_io: disabling / tsp_avdd: disabling      (t=2.24 s)
/proc/bus/input/devices: no sec_touchscreen at all
/sys/class/sec/tsp: absent      /proc/interrupts: no sec_ts line
```

`androidboot.mode=` is consumed by `sec_bat_is_lpm_check()` (`__setup`), which sets
`lpcharge=1`; `sec_ts_init()` then returns `-ENODEV` (`Do not load driver due to :
lpm 1`, documented in DEVICE-OBSERVATIONS.md §385) and the i2c client 4-0048 is
never bound. No userspace action can repair this - the driver's initcall has
already run.

**The lever that works without touching the phone:** a Linux-initiated
`reboot` **does not** re-enter charger mode, even with USB attached. After
`sync; nohup reboot`:

```
uptime 0 min      androidboot.mode=  (absent)     → normal, non-LPM boot
sec_touchscreen as /devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2
/proc/interrupts: 431: 8 ... sec_ts       /sys/class/sec/tsp/ present (cmd, cmd_list, status …)
```

This corrects PHONE-UI-HANDOFF.md §3b ("reboot with USB detached"): the detach is
unnecessary; the *mode* is what matters, and an OS reboot clears it.

### 8.2 Arming the panel: the measured sequence

`sec_ts_input_open()` short-circuits whenever the driver's `power_status` is
already `POWER_ON` (`already power on` → `Failed to start device` → no
`enable_irq()`), and the display notifier calls it every ~2 s while anything drives
`fb0/blank`. The only path that reaches `SENSE_ON` + `enable_irq()` is
`sec_ts_start_device()` after a *real* stop:

```sh
echo module_off_master > /sys/class/sec/tsp/cmd     # OK (cmd_result read back)
echo 1 > /sys/class/graphics/fb0/blank              # notifier: FB_BLANK_NORMAL
echo 0 > /sys/class/graphics/fb0/blank              # notifier: FB_BLANK_UNBLANK -> real start
```

`nuxel-touch-arm` now does exactly this (tsp cmd → read back `cmd_result` with a
timeout → `fb0` blank 1→0 → hold a reader fd open) and appends its evidence to
`/run/nuxel-touch-arm.state`. Two measured corrections to the A29 record:

| A29 claim | A29b measurement |
|---|---|
| `module_on_master` from userspace is harmless | **Wrong**: right after it the controller sat at `sec_ts_i2c_read: POWER_STATUS : OFF` and stopped sensing (IRQ 14→14 over a tap window). It is no longer issued. |
| `module_off_master` answers `NG`/`EBUSY` because of the notifier storm | It answers **OK** (`module_off_master:OK` at t=1368.6 s and again at t≈1630 s); EBUSY is transient, so the helper retries and reads the result back. |
| `open()` after the stop runs the real start | **Only when no other client holds the node.** libinput inside phoc keeps `dev->users > 0`, so a client open does not re-run `input_open`; the notifier must be driven instead (§8.2). |

### 8.3 Touch results (P0)

```
/proc/interrupts sec_ts:  16 -> 225  (60 s tap window),  304 -> 565
/sys/class/sec/tsp/all_touch_count: TTCN 2      read_all_touch_count_show: touch:2
kernel:  [P] tID:0.0 z:63 major:26 minor:10 loc:E.C tc:1
         [P] tID:2.1 z:63 major:23 minor:15 loc:C.N tc:2
         [R] tID:2 loc:C.N dd:20,-2 mp:5,0 mc:3 tc:1 p:0     (release after a swipe)
userspace (our own reader on /dev/input/event2):
         /run/nuxel-touch-arm.state:  "TOUCH_POINT slot=0 n=217"
compositor: phoc holds 7 /dev/input/eventN fds (libinput) -> events reach the session
```

So the complete pipeline TOUCH CONTROLLER → sec_ts → evdev → userspace is verified
with physical fingers, taps *and* a swipe (`dd:20,-2`).

### 8.4 Three launcher defects found and fixed (the reason the screen was blank)

1. **Docroot/URL.** `build-phone-rootfs-inside-fedora.sh` staged only
   `pwa/nuxel-home` as `/usr/share/nuxel/nuxel-home`, but `index.html` line 125
   imports `../nuxel-common/bridge.js` (enforced by
   `pwa/nuxel-common/verify-wiring.js`) and the VM's `services/nuxel-web.service`
   serves the repository root. Result: 404 for `/pwa/nuxel-home/index.html` *and*
   for the bridge module. Fixed live (`/usr/share/nuxel/pwa/` + the 5
   `nuxel-common` files, each SHA-256 verified on the target; `nuxel-session.sh`
   now detects the layout and reports `layout=… bridge_ok=…`), fixed in the builder
   (§8.6).
2. **WebKit crash on the launcher's splash video.** `autoaudiosink` is absent from
   the handset image (no `gstreamer1-plugins-good` → no
   `libgstautodetect.so`), so WebKit 2.52.5's playbin path printed
   `GStreamer element autoaudiosink not found` → `invalid (NULL) pointer instance`
   → the **WebKitWebProcess died** (`terminated abnormally`, 00:07:45Z) and the
   view stayed blank forever. A media-free page proved the engine itself is fine
   (`NUXEL_HOME_READY`, web process alive). `nuxel-pwa-host` now enables media only
   where the audio sink exists (`NUXEL_HOME_MEDIA enable_media=… audio_sink=…` in
   the state file); the launcher degrades by design (`js/app.js` hides
   `#boot-splash` on the video's `error` event + a 12 s timeout) and the phone's
   original boot animation is played from the initramfs before this view exists.
3. **Two framebuffer owners.** `/init` re-enables `nuxel-ui.service` into
   `multi-user.target.wants` *and* `sysinit.target.wants` every boot, and the
   initramfs postboot supervisor (`tools/s10plus/a24/nuxel-postboot.sh`) restarts it
   every 30 s: measured `Stopped nuxel-ui` 00:03:07 → `Started nuxel-ui` 00:03:16.
   `systemctl mask` cannot be used (the unit file itself lives in
   `/etc/systemd/system`), so the durable fix is a drop-in condition
   (`/etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf`,
   `ConditionPathExists=!/usr/lib/nuxel/nuxel-wl-fb` → `ConditionResult=no`,
   unit skipped), plus the launcher units enabled
   (`nuxel-touch-arm nuxel-wayland nuxel-wl-fb nuxel-fallback`) and
   `nuxel-ui.service` disabled. The A27 UI is still available as the fallback
   *process* through `nuxel-fallback.service`. `init.sh` and `nuxel-postboot.sh`
   are patched in the repository so future BOOT images stop re-enabling it.

### 8.5 Verified end state on the handset (live)

```
/run/nuxel-session.log:  session start … layout=/pwa/nuxel-home bridge_ok=yes url=http://127.0.0.1:8000/pwa/nuxel-home/index.html
                         web server pid=6529 ready=yes
/run/nuxel-home.state:   NUXEL_HOME_MEDIA enable_media=0 audio_sink=0
                         NUXEL_HOME_OPEN url=…/pwa/nuxel-home/index.html engine=WebKitGTK/2.52
                         NUXEL_HOME_COMMITTED / NUXEL_HOME_READY (real page, no 404)
                         WebKitWebProcess alive (pgrep -fc WebKitWebProcess = 1)
/run/nuxel-wl-fb.state:  FB_OPEN_OK … / FRAMES_OK total=447 fps_1s=447 failures=0
                         out=720x1520 src=720x1520 scale=2 panel=1440x3040
systemd:                 nuxel-wayland active, nuxel-wl-fb active, nuxel-touch-arm active,
                         nuxel-ui inactive (ConditionResult=no) and disabled
```

Deployed binaries (each SHA-256 verified on the target): `nuxel-pwa-host
1fec1b18…`, `nuxel-touch-arm 2d1f6ef4…`, `nuxel-session.sh 848255f5…`,
`nuxel-wl-fb c1c468ae…` (unchanged this cycle), `nuxel-common/*` (5 files),
`10-launcher-primary.conf 9abb859c…`.

### 8.6 Repository changes (so a fresh image ships the working configuration)

* `images/s10plus/build-phone-rootfs-inside-fedora.sh` — stages the whole `pwa/`
  tree (with the flat path kept as a symlink for `verify-fedora-phone-rootfs.py`),
  installs the `nuxel-ui` launcher-primary drop-in, enables
  `nuxel-touch-arm nuxel-wayland nuxel-wl-fb nuxel-fallback`
  (`NUXEL_ENABLE_LAUNCHER=0` builds the old fb-UI-only image; the size guard now
  also covers the `pwa/nuxel-apps` payloads).
* `boot/initramfs/init.sh` — does not enable `nuxel-ui.service` when
  `/usr/lib/nuxel/nuxel-wl-fb` is present (takes effect with the next BOOT build).
* `tools/s10plus/a24/nuxel-postboot.sh` — is launcher-aware: it starts the
  launcher units and never starts the A27 UI while the launcher owns the panel
  (initramfs copy; next BOOT build).
* `tools/s10plus/a29/` — `nuxel-session.sh` (layout detection),
  `nuxel-touch-arm.c` (deterministic arming, append-only evidence),
  `nuxel-pwa-host.c` (media gate), `nuxel-ui-launcher-primary.conf`, refreshed
  binaries + `SHA256SUMS`.

### 8.7 Still open (honest list)

* **Visual confirmation on the glass** — I cannot see the panel; the user confirms
  what the AMOLED shows. What is *proven* is: composited frames are written to the
  panel every second (`FRAMES_OK`), the page reached `NUXEL_HOME_READY`, and 217
  touch points reached a userspace reader.
* **Tap → app launch.** The registry's web apps (`/pwa/nuxel-apps/…`) need the
  staged `pwa/` tree; the custom-scheme apps (`nuxel-camera://`,
  `nuxel-settings://`, …) need the native bridge, which is not running
  (`nuxel-common/bridge.js` asked for `/var/lib/nuxel/.api-token` → 404 in
  `/run/nuxel-web.log`). App-launch parity with the VM is therefore **not yet
  claimed**; next lever is the VM's `nuxel-http-bridge` equivalent on the phone.
* **Frame rate** under software rendering has not been measured beyond the
  bridge's own `fps_1s` counter.
* A kernel with `CONFIG_DRM=y` would remove the screencopy→fbdev bridge entirely
  (separate, boot-partition-write project).
