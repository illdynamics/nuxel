# PWNAGE-54000 — orientation, navigation, icons and CPU

**Date:** 2026-11-01
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
**Transport:** Wi-Fi SSH `root@192.168.178.167`, key `~/.ssh/wicked_wqn_id_rsa`
**Kernel:** `4.14.253-gf7194c1d15ed-dirty #5` (no kernel/firmware/partition write)
**Deployed userspace backup:** `/var/backups/nuxel/p54000-20261101T154832Z`
**Follow-up shim backup:** `/usr/lib/nuxel/libnuxel-libinput-path.so.p54000-prev2`

## 1. Root cause

### 1.1 The working rotation was the compositor transform

The live Phoc session exposes **`HEADLESS-1`**, not `DSI-1`. Its mode is
`720x1520`, and `wlr-randr --json` is the only truthful output inventory.
`wlr-randr --output HEADLESS-1 --transform 90` is accepted and the compositor
changes the transform. The historical mapping was therefore the path that
worked:

| canonical pose | compositor transform | scale | verified logical output |
|---:|---:|---:|---|
| 0° | `normal` | 2 | 360×760 |
| 90° | `270` | 1 | 1520×720 |
| 180° | `180` | 2 | 360×760 |
| 270° | `90` | 1 | 1520×720 |

The reverse 90/270 mapping is deliberate. It is the physical mapping recovered
from the historical configuration, not a mathematical simplification.

`--transform 90 --scale 2` does rotate the scene, but leaves the logical desktop
at 760×360. That produced a sideways picture without landscape geometry and was
one source of the “partial success” reports. `--scale 1` in landscape gives the
real 1520×720 RFB/logical desktop. The daemon now applies transform **and**
scale as one transaction.

### 1.2 The presenter was stale

`images/s10plus/build-phone-rootfs-inside-fedora.sh` compiles
`tools/s10plus/a67/nuxel-wl-fb.c`. The rotation-capable code had been written
into the unused `a34` tree. The live `a67` bridge had no orientation support and
published no glass-side proof. The fix keeps `nuxel-wl-fb` as the **sole
`/dev/fb0` writer** and adds only `/run/nuxel-wl-fb.orientation` evidence:
capture dimensions, panel dimensions, requested/compositor transform, scale and
`presenter_rotation=0` / `double_rotation=0`.

The presenter must **not** rotate again: wlroots transforms the rendered scene
and the screencopy buffer, but **not** `wlr_touch` events. Touch therefore needed
a separate, coordinated owner (section 1.7).

### 1.3 Every successful rotation was silently reverted

`do_set(..., apply_now=False)` explained the original preference-only behavior.
The later uncommitted code added `--apply` but wrapped every successful mode
change in a 75 s “owner confirmation” trial. Nothing ever confirmed it, so a
successful transform reverted after 75 s. The Bridge/UI therefore looked like it
saved a preference and then undid it.

The normal `set` path now commits a transform only after live readback; a failed
apply restores the previous verified transform and keeps the previous policy.
`--trial` is now explicit opt-in (15–90 s) for owner acceptance tests only.

### 1.4 Triple navigation was blocked by a stale lock cache

Live trace with `NUXEL_INPUT_DIAG=1` proved the host action arrived:

```
EVT nav:action recents locked=1
```

The authoritative provider file `/run/nuxel/security/lock-state.json` said
`"locked": false`, but the launcher's local boot-gate cache still said locked, so
`_isLocked()` discarded every Back/Home/Recents request. The launcher now:

* reconciles the boot gate against `security.status` at startup;
* replays a host/dock action only after the provider confirms `locked=false`;
* never bypasses a genuinely locked provider.

After the fix the live trace is:

```
EVT lockscreen:boot-authority-unlocked
EVT nav:action recents locked=0
RECENTS state=OPEN reason=system-nav
EVT nav:action back locked=0
EVT nav:action back-long locked=0
app:lifecycle id=nuxel-settings state=CLOSING
home:complete state=CLOSED page=0
```

### 1.5 Recents/tabs endpoint mismatch

`pwa/nuxel-home/js/recents.js` used `GET /api/v1/windows/list`; the Bridge route
existed only under `POST`, so native tabs always received `{"error":"Not found"}`.
GET is now implemented, native close is a separate `/api/v1/windows/close`, and
the Recents card has a real Close button plus left-swipe close. Long Back now
uses the foreign-toplevel `close` opcode and a bounded stop of that app's own
`nuxel-app-*` transient units; it never touches Home, Phoc, the Bridge or a
system service.

### 1.6 Touch was never transformed by the compositor

This corrects an earlier assumption in this report. Phoc 0.54.0 feeds raw
libinput touch coordinates through `wlr_cursor_absolute_to_layout_coords()`; the
wlroots cursor helper applies an output transform to absolute pointer devices,
not to touch. The displayed landscape desktop therefore had portrait-mapped
touch, exactly matching the owner symptom (bottom-left taps landing at the
top-left after a landscape rotation).

The image relationship was measured rather than guessed: for a live transform
`270`, `nuxel-screenshot` returns the 720x1520 raw buffer and `grim` returns the
1520x720 logical desktop, with `raw == np.rot90(logical, 3)` to zero MAE. That
means the portrait touch frame must be rotated 270 degrees clockwise into the
logical desktop. The libinput matrix is `0 1 0 / -1 0 1`.

`libnuxel-libinput-path.so` is already the single LD_PRELOADed input-discovery
owner inside Phoc. It now also reads `/run/nuxel-orientation/input.json`, applies
the matrix through `libinput_device_config_calibration_set_matrix()`, reads it
back, and records `/run/nuxel-touch-calibration.state`. An inotify thread inside
that same shim makes the change immediate while the screen is idle. There is no
second daemon, polling policy, presenter touch rotation, or duplicate matrix.

### 1.7 Microphone was disabled in the WebKit host

The ALSA/ABOX route and PipeWire source were present
(`alsa_input.hw_0_13`, `S10+ microphone (WDMA1, 48 kHz)`), and the Bridge
`audio.capture-route` returned `available=true`. The webview did not enable
`enable-media-stream`, and its audio permission branch could depend on WebKit
reporting the old audio flag. The A45 host now enables MediaStream explicitly,
allows an audio-only request from the exact Recorder page, and keeps video/camera
denied. The `nuxel-portal` crash loop was separately fixed by granting the
`nuxel` user traverse access to `/var/lib/nuxel` and adding the
`nuxel-notifications` supplementary group to the unit.

### 1.8 Sensor truth

The current kernel still exposes the LSM6DSO only through the Samsung SSP hub.
`/sys/class/sensors/accelerometer_sensor/raw_data` reads `0,0,0`; the IIO stub
has no readable accelerometer scale; `iio-sensor-proxy` is absent; dmesg reports
`ssp_down` / `ssp_send_cmd ... failed -1`. Auto modes remain selectable but are
reported `auto_state=blocked_sensor_unavailable`. No manual source is marked
auto-capable. Fixed modes require no sensor and all four now verify.

## 2. Files changed

| File | Purpose |
|---|---|
| `configs/nuxel/orientation/orientation.json` | exact labels, historical transform map, portrait/landscape scale, commit semantics |
| `services/nuxel-orientation/nuxel_orientation/policy.py` | exact seven labels |
| `services/nuxel-orientation/nuxel_orientation/apply.py` | `scale_for`, transform+scale application, logical-geometry readback |
| `services/nuxel-orientation/nuxel-orientationd` | terminal result wait, verified commit, rollback, sequence/transition/remote status |
| `services/nuxel-bridge/src/bridge.py` | verified `--apply` unchanged; status proxy |
| `services/nuxel-bridge/src/api.py` | GET windows/list, targeted windows/close, bounded force-stop |
| `tools/s10plus/a67/nuxel-wl-fb.c` | glass-side orientation proof, no double rotate, faster idle cadence |
| `tools/s10plus/a33/nuxel-libinput-path.c` (and byte-identical A31 copy) | single libinput touch-calibration owner, immediate inotify updates, read-back evidence |
| `tools/s10plus/a45/nuxel-pwa-host.c` | enable `enable-media-stream`; permit audio-only Recorder capture |
| `services/nuxel-portal/src/portal.py`, `systemd/nuxel-portal.service` | fix permission-store traversal failure |
| `configs/libinput/nuxel-s10plus-touch.conf` | document dynamic matrix ownership, no static double transform |
| `tools/s10plus/a59/nuxel-foreign-toplevel.c` | close-foreground and targeted close verbs |
| `pwa/nuxel-home/js/app.js` | lock-authority reconciliation, action tracing |
| `pwa/nuxel-home/js/recents.js` | GET endpoint, Close button, left-swipe close |
| `pwa/nuxel-home/js/qs.js` | exact labels, truthful applied/state/VNC status |
| `pwa/nuxel-apps/settings/settings.js` | exact labels, sensor/output/touch/remote diagnostics |
| `pwa/nuxel-home/index.html`, `css/status-bar.css`, `assets/.../*.svg` | Bluetooth rune and classic location pin |
| `services/nuxel-remote-desktop/bin/nuxel-orientation-remote-sync` | asynchronous VNC/XRDP consumer and per-session truth |
| `services/nuxel-remote-desktop/config/xrdp.ini` | Xvnc backend (runtime RandR resize) |
| `images/s10plus/build-phone-rootfs-inside-fedora.sh` | a67 presenter, remote helper, xrandr, assets |
| `tools/s10plus/a67/deploy-pwnage54000.sh`, `rollback-pwnage54000.sh` | safe Wi-Fi userspace deploy/rollback |
| `tests/pwnage54000/test_pwnage54000.py` | regression contracts |
| orientation tests + `tests/pwnage46000/test_rotation_contract.py` | new exact-label/scale/commit contracts |

## 3. Automated tests

```
pytest services/nuxel-orientation/tests tests/pwnage46000 tests/pwnage54000 -q
84 passed
```

`node --check` passes for `app.js`, `recents.js`, `qs.js` and `settings.js`.
`nuxel-orientationd selftest` passes on the phone.

## 4. Live device evidence

### 4.1 Four fixed poses (daemon + wlr-randr)

```
portrait          success=true effective=0   applied=true verified=true transform=normal scale=2 logical=360x760
landscape         success=true effective=90  applied=true verified=true transform=270  scale=1 logical=1520x720
reverse-portrait  success=true effective=180 applied=true verified=true transform=180  scale=2 logical=360x760
reverse-landscape success=true effective=270 applied=true verified=true transform=90   scale=1 logical=1520x720
```

Live libinput read-back (`/run/nuxel-touch-calibration.state`):

```
normal  1,0,0,0,1,0
180    -1,0,1,0,-1,1
270     0,1,0,-1,0,1
90      0,-1,1,1,0,0
```

Glass-side proof (`/run/nuxel-wl-fb.orientation`) for landscape:

```
requested_transform=270
compositor_transform=3
capture=720x1520
panel=1440x3040
effective_orientation=90
scale=1
frame_ok=1
presenter_rotation=0
double_rotation=0
```

### 4.2 VNC

* wayvnc mirrors the live Phoc output.
* RFB probe: `1520x720` for landscape (transform 90/270 scale 1), `720x1520`
  for portrait (normal/180 scale 2).
* `/run/nuxel-orientation/remote.json` reports the verified logical size,
  capture-buffer size, client count and `status=mirrored`.
* Live RFB probe: a new VNC session started while portrait advertised
  `720x1520`; after switching landscape and restarting the server it advertised
  `1520x720`. New/reconnected sessions therefore inherit current orientation.
* The existing wayvnc control API does not expose a force-resize command. An
  already-connected client depends on wayvnc's automatic resize and the client's
  DesktopSize support; this is reported separately from local success.

### 4.3 XRDP

The Xorg backend (`xorgxrdp` `rdp0`) rejects server-side rotation with
`BadMatch (RRSetCrtcTransform)` and rejects `--fb`/mode changes. XRDP therefore
now prefers the TigerVNC (`Xvnc`, `VNC-0`) backend, which accepts runtime RandR
mode changes.

Live session (`Xvnc :10`, PID unchanged throughout):

```
portrait           720x1520  synchronized exact=true
reverse-portrait   720x1520  geometry_axis_matches_rotation_unsupported exact=false
landscape          1520x720  synchronized exact=true
reverse-landscape  1520x720  geometry_axis_matches_rotation_unsupported exact=false
```

The Xvnc PID and Firefox processes stayed alive; the desktop was resized, not
logged out or restarted. New sessions start at the client-requested geometry and
the asynchronous sync immediately moves them to the phone orientation. The
daemon also runs this consumer once every 10 s, so a new session is detected and
a vanished session is pruned even when the orientation did not change; it is one
shared consumer refresh, not a per-session polling loop.

### 4.4 Navigation

```
EVT lockscreen:boot-authority-unlocked
EVT nav:action settings locked=0
EVT nav:action back locked=0
EVT back:pwa-at-root
EVT nav:action back-long locked=0
app:lifecycle id=nuxel-settings state=CLOSING
home:complete state=CLOSED page=0
```

Back at a PWA root is a safe no-op inside the app; long Back closes the
foreground app; Home returns to Desktop 1; Recents opens and closes.

### 4.5 CPU

Idle `nuxel-wl-fb` capture is now `fps_1s=1`, `idle_ms≈9000`, and the bridge no
longer appears in the top CPU list. The drop-in cap is `NUXEL_TARGET_FPS=20`
(active interaction), with 8/3/1 fps idle tiers. Load average remains ~12 because
of Samsung TrustZone D-state kthreads, not userspace CPU.

## 5. Remaining limitations (honest)

1. **Accelerometer/Auto** — hardware/SSP firmware unavailable on this kernel.
   Auto modes are truthful `blocked_sensor_unavailable`; no simulated success.
2. **XRDP reverse poses** — Xvnc changes the geometry axis but cannot invert the
   framebuffer. 0° and 90° are exact; 180° and 270° get the correct axis
   (720×1520 / 1520×720) and are reported as
   `geometry_axis_matches_rotation_unsupported`. No session is killed.
3. **Xorg XRDP backend** — `rdp0` cannot resize at runtime; Xvnc is the shipped
   default. The Xorg entry remains a manual fallback.
4. **Touch owner verification** — `libnuxel-libinput-path.so` is the single
   touch transform owner and applies a libinput calibration matrix. Runtime
   transform + matrix read-back is verified for all four poses. A physical
   four-corner finger test is still required because an SSH agent cannot press
   the glass; `touch.verified` remains false until the owner confirms it.
5. **Microphone** — the real WebKitGTK capture probe now returns a live track
   labelled `S10+ microphone (WDMA1, 48 kHz)`; physical audible-content capture
   still needs an owner recording test.
6. **Jump Desktop** — tested live against the VNC mirror after reboot. Jump
   Desktop stayed connected (`wayvncctl client-list` = 1 client) through
   portrait, landscape, reverse-portrait and reverse-landscape. The server
   reported 360×760 logical for portrait/reverse-portrait and 1520×720 for
   landscape/reverse-landscape. Jump's window stayed 1512×746 for every pose,
   so it scales/letterboxes rather than resizing its window on RFB DesktopSize;
   this is a client-specific presentation limitation, not a server failure.
   Evidence: `evidence/pwnage-54000/jump-desktop-landscape.png`.

## 6. Wi-Fi SSH deployment and rollback

```sh
# deploy (backs up every replaced file, rebuilds native tools on-device)
tools/s10plus/a67/deploy-pwnage54000.sh root@192.168.178.167

# rollback
tools/s10plus/a67/rollback-pwnage54000.sh root@192.168.178.167 \
  /var/backups/nuxel/p54000-<timestamp>
```

The script never writes BOOT, firmware or a partition. It keeps
`/usr/lib/nuxel/nuxel-wl-fb.p54000-prev` until the next reboot proves the new
build. The rollback restores the orientation package/config, PWA tree, assets,
navdock and foreign-toplevel, then restarts only the orientation daemon,
Bridge and Wayland session.

## 7. Post-reboot acceptance

After the requested reboot (SSH returned after 60 s):

```
nuxel-orientationd active
nuxel-wayland     active
nuxel-wl-fb       active
nuxel-http-bridge active

mode=landscape  mode_label=Locked (LS)  effective=90
applied=true    display_verified=true
output=HEADLESS-1 transform=270 scale=1 logical=1520x720
/run/nuxel-wl-fb.orientation:
  requested_transform=270
  compositor_transform=3
  capture=720x1520 panel=1440x3040
  effective_orientation=90 scale=1 frame_ok=1
  presenter_rotation=0 double_rotation=0
```

The saved policy was restored from `/var/lib/nuxel/orientation/state.json`.
The security provider correctly booted fail-closed with no state file; after the
authoritative swipe unlock the native dock mapped (`NAV_DOCK_SHOW lock=unlocked`).
Immediately after boot the host reported 98.9% CPU idle and the framebuffer
bridge was at the 1 fps idle tier.

Final deployed hashes:

```
8ad9c09ae93b6d693b5c9fa03cc9655da9ab19fd3f1aa55ea14a93d7b2cfcab2  nuxel-orientationd
45bb5546f5c315680494286ef4cce151cfc8ed14532fbee169da5d82b6ced944  nuxel-wl-fb
368f96e9b749195b3a91d5b809239924cd53738719a41cc882bb814672b48faa  nuxel-navdock
660346087b93bd08dcbb16f71c4072280367432e8f781fb57605e49616d58dd4  nuxel-foreign-toplevel
```


## 8. Jump Desktop live result

With Jump Desktop connected to `192.168.178.167:5900`:

```
portrait           wayvnc client-list: 1   server logical: 360x760
landscape          wayvnc client-list: 1   server logical: 1520x720
reverse-portrait   wayvnc client-list: 1   server logical: 360x760
reverse-landscape  wayvnc client-list: 1   server logical: 1520x720
```

The Jump window remained 1512×746 in every pose; the remote session was never
disconnected. Jump therefore letterboxes/scales instead of resizing its macOS
window. The phone's local rotation and the VNC framebuffer geometry were
correct in every pose.
