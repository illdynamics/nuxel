# FULL-PWNAGE-46000
# NUXEL — COMPLETE PHYSICAL SCREEN ROTATION, TOUCH TRANSFORM, SENSOR AUTO-ROTATION, SEVEN MODE POLICY AND NOTES-DRIVEN HUMAN VERIFICATION

## Source-level repair, active-image integration, safe live deployment and iterative physical-device acceptance mission

**Mission ID:** PWNAGE-46000  
**Target device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel — custom Fedora-based ARM64 Linux mobile OS  
**Primary compositor/session:** Phoc / Wayland  
**Display presentation:** Wayland `zwlr_screencopy` → `nuxel-wl-fb` → Samsung DECON / `/dev/fb0`  
**Touch input:** existing Linux input → seatd/libinput → Phoc path  
**Rotation policy source:** `configs/nuxel/orientation/orientation.json`  
**Policy implementation:** `services/nuxel-orientation/`  
**Bridge integration:** `services/nuxel-bridge/src/bridge.py` and its `orientation` RPC methods  
**UI:** `pwa/nuxel-home/js/qs.js`, `pwa/nuxel-apps/settings/settings.js` and Settings markup  
**Human feedback channel:** Nuxel Notes app, Bridge storage key `nuxel-notes`  
**Mission type:** end-to-end display and input implementation, continuous service, real sensor integration, live test/fix iterations, packaging, regression testing and owner-confirmed completion.

---

# 0. MISSION STATEMENT

The purpose of this mission is to make screen rotation genuinely work on the physical Samsung Galaxy S10+ running Nuxel. The existing UI and policy already describe seven modes, but that does not prove a physical rotation occurs. The agent must trace and repair the full pipeline from the user's selected policy through the orientation service, real sensor events, compositor/output geometry, framebuffer presentation, touchscreen-coordinate transform and application viewport.

This is **not** a CSS-only feature, not an icon/toggle makeover and not a task that is complete when a JSON setting changes. The phone must remain physically usable after rotation. Text must be upright and correctly laid out; touch points must land on the controls beneath them; the keyboard, dock, status bar, lockscreen, Notes app and app windows must remain usable.

The owner will physically test the handset and answer through Notes. The agent must keep iterating through the loop:

**inspect → change → automated-test → build → safely deploy → ask owner to test → read Notes feedback → diagnose failure → change → repeat.**

Do not stop at an arbitrary three attempts. Continue for as long as the failure is fixable in source/userspace and the owner is willing to test. Stop only when all required tests pass, the user cancels, or a real hardware/kernel/firmware prerequisite is proven and cannot safely be satisfied within this userspace mission. In that case, report an exact blocker and the required next artifact; never claim success from an offline/mock result.

---

# 1. THE SEVEN REQUIRED MODES AND EXACT SEMANTICS

Implement exactly these seven modes, with these exact visible labels and behavior:

| Order | Visible label | Canonical key | Allowed effective degrees | Meaning |
|---:|---|---|---|---|
| 1 | **Auto** | `auto` | `0, 90, 180, 270` | Full automatic rotation: normal portrait, normal landscape, reverse portrait and reverse landscape. |
| 2 | **Auto (PT)** | `auto-portrait` | `0, 180` | Automatic portrait-only rotation: portrait and reverse portrait are allowed; both landscape positions are forbidden. |
| 3 | **Auto (LS)** | `auto-landscape` | `90, 270` | Automatic landscape-only rotation: normal and reverse landscape are allowed; both portrait positions are forbidden. |
| 4 | **Portrait** | `portrait` | `0` | Manually locked to native/normal portrait. Physical movement must not change the screen orientation. |
| 5 | **Landscape** | `landscape` | `90` | Manually locked to the chosen normal landscape direction. Physical movement must not change the screen orientation. |
| 6 | **RPortrait** | `reverse-portrait` | `180` | Manually locked to reverse/upside-down portrait. Physical movement must not change the screen orientation. |
| 7 | **RLandscape** | `reverse-landscape` | `270` | Manually locked to the opposite landscape direction. Physical movement must not change the screen orientation. |

The currently checked-in configuration already uses these seven canonical hyphenated keys and their correct allowed degree sets. Preserve those stable values and the existing underscore-key migration aliases. Update the presentation labels to the exact strings above. Do not rename stable IDs merely to make the labels shorter.

## 1.1 Define angle semantics precisely

Use `0°` as the handset's native portrait orientation. Use `180°` as the reverse portrait pose. `90°` and `270°` are the two opposite landscape poses, but do not blindly assume the current sensor-axis mapping or compositor transform map is correct.

The user-facing `Landscape` mode should be one consistent, documented physical landscape direction; `RLandscape` is the opposite direction. Determine and calibrate which physical pose corresponds to each direction by testing the actual S10+ while facing the display. Record the reference pose in the orientation documentation and in the status output.

Distinguish:

- **physical handset pose**: how the user is holding the phone relative to gravity;
- **effective content orientation**: which of the four logical screen poses the UI is currently using;
- **compositor/output transform**: how Wayland maps logical content to the physical panel;
- **framebuffer scanout orientation**: the orientation of the pixel memory/DECON panel;
- **touch coordinate transform**: how hardware touch coordinates map to the logical Wayland surface.

These are related but not interchangeable. A correct orientation implementation keeps all of them mutually consistent.

## 1.2 Auto policy behavior

- `auto`: any one of the four positions may become effective based on the real gravity vector.
- `auto-portrait`: only `0` or `180` can be effective. When the phone is turned sideways, it must keep the last allowed portrait orientation rather than rotating into landscape.
- `auto-landscape`: only `90` or `270` can be effective. When the phone is held upright, it must keep the last allowed landscape orientation rather than rotating into portrait.
- Flat/ambiguous poses must not flap between orientations. Keep the last known good permitted orientation until the sensor produces a stable, unambiguous new pose.
- Auto modes must not advertise active automatic behavior when no real accelerometer/gravity source is available. They may be selectable, but the UI must clearly display `sensor unavailable` / `auto blocked` and the service must not invent movement.
- When entering `auto-portrait` from a landscape state, choose a valid portrait initial pose immediately: use a real stable sensor pose if available; otherwise prefer `0°` or the last remembered permitted portrait pose.
- When entering `auto-landscape` from a portrait state, choose a valid landscape initial pose immediately: use a real stable sensor pose if available; otherwise prefer `90°` or the last remembered permitted landscape pose.
- Switching modes must update the selected policy and apply a safe valid effective orientation in one coherent transaction. The selected mode must never have an effective orientation outside its `allowed` list.

## 1.3 Manual mode behavior

The four fixed modes do not require an accelerometer. They must work even if the S10+ sensor hub is offline.

- Selecting `Portrait` applies `0°` and stays there when tilted to either landscape or upside-down.
- Selecting `Landscape` applies `90°` and stays there when tilted to portrait, reverse portrait or reverse landscape.
- Selecting `RPortrait` applies `180°` and stays there during physical movement.
- Selecting `RLandscape` applies `270°` and stays there during physical movement.

A manual mode must not be implemented as “turn off the sensor but retain the old frame”; it must explicitly apply the requested output transform and logical dimensions.

---

# 2. SOURCE AUDIT — CONCRETE FINDINGS IN THE PROVIDED REPOSITORY SNAPSHOT

The following findings were verified by reading `nuxel-main (10)(1).zip` on 31 October 2026. First verify that the current worktree and live device still match these files; do not use a historical finding to skip the live check.

## 2.1 Existing orientation policy

`configs/nuxel/orientation/orientation.json` already contains:

- schema version 1;
- S10+ / `beyond2lte` device metadata;
- the seven named modes and allowed orientation degrees;
- mode order `auto`, `auto-portrait`, `auto-landscape`, `portrait`, `landscape`, `reverse-portrait`, `reverse-landscape`;
- safe default `portrait`;
- debounce, hysteresis and flat-phone policy values;
- IIO and `iio-sensor-proxy` sensor source definitions;
- an unverified sensor mount matrix;
- unverified gravity reference vectors;
- an unverified compositor transform map;
- state-file, FIFO and log paths.

The existing transform map is:

```json
{
  "0": "normal",
  "90": "270",
  "180": "180",
  "270": "90"
}
```

This is an intended inverse relationship between the physical pose and compositor transform, but the file itself explicitly says it has not been calibrated on the handset. Do not mark it verified merely because the table exists. Test it physically and correct it if the display rotates in the wrong direction.

## 2.2 Policy module already implements seven modes

`services/nuxel-orientation/nuxel_orientation/policy.py` defines the seven stable modes and legal degree sets. It also normalizes legacy underscore aliases:

- `auto_portrait` → `auto-portrait`
- `auto_landscape` → `auto-landscape`
- `reverse_portrait` → `reverse-portrait`
- `reverse_landscape` → `reverse-landscape`

Keep a single migration boundary. All persisted state and RPC inputs must normalize through the policy module. Old settings must not appear as `undefined` or create duplicate modes.

Current labels are `Forced Portrait`, `Forced Landscape`, `Auto Portrait`, `Auto Landscape` and advanced reverse labels. Change visible labels to the exact requested text without changing stable keys or allowed values.

## 2.3 Existing Quick Settings and Settings UI

The Quick Settings Rotate tile in `pwa/nuxel-home/js/qs.js` already:

- reads the current orientation using `bridge.call('orientation', 'get', {})`;
- tap-toggles `auto` and `portrait`;
- long-presses to build a seven-mode menu;
- calls the `orientation.set` Bridge operation;
- refreshes the displayed state and OSD.

The current menu labels are longer than requested. Replace them with `Auto`, `Auto (PT)`, `Auto (LS)`, `Portrait`, `Landscape`, `RPortrait`, `RLandscape`. Keep all seven options visible and reachable. Do not accidentally hide reverse modes in a submenu or mark them “advanced” if the owner explicitly wants them in the primary mode list.

The Settings rotation panel in `pwa/nuxel-apps/settings/index.html` and `settings.js` already builds radio choices and displays effective orientation/sensor/calibration state. Update labels and status display. It should show:

- selected policy;
- effective physical/content orientation in degrees and human label;
- sensor availability and source;
- calibration verification;
- current output name and actual backend;
- whether the transform is applied;
- whether touch calibration is verified;
- any last error or fail-safe rollback state.

Never show a successful “applied” message when only a preference was saved.

## 2.4 Bridge command path currently does not request apply

`services/nuxel-bridge/src/bridge.py` contains `OrientationConnector` with default binary:

`/usr/libexec/nuxel/nuxel-orientationd`

Its current `set_mode()` calls the helper with `set <mode>`. It does not append `--apply`.

In `services/nuxel-orientation/nuxel-orientationd`, `do_set(config, mode, apply_now=False)` persists the selected mode and only invokes `apply_mod.apply_transform()` when `apply_now=True`.

Therefore the current UI can change and persist a mode while never trying to rotate the actual screen. This is a critical end-to-end integration flaw. Change the API contract so the default user-facing `orientation.set` operation initiates a safe apply transaction (with the watchdog and rollback described below), or delegate the operation through a proper long-running daemon. Do not merely append `--apply` and then pretend that an unsupported compositor transform has succeeded.

The Bridge return value must separate at least:

- `success` / request accepted;
- `mode` / selected policy;
- `effective_orientation`;
- `applied` / actual output transform result;
- `backend` and output identifier;
- sensor availability/source for auto modes;
- touch transform availability/verification;
- blocker/error details;
- trial/rollback state when a human confirmation is pending.

## 2.5 `wlr-randr` availability check has a code defect

`services/nuxel-orientation/nuxel_orientation/apply.py` currently checks availability by running:

`subprocess.run(["command", "-v", "wlr-randr"], ...)`

`command` is a shell builtin, so it is not generally an executable that can be invoked this way. Replace this with `shutil.which("wlr-randr")` or a correctly scoped executable lookup. Do not use `shell=True` for this check.

This fix only detects whether `wlr-randr` exists. It does not prove that the active compositor exposes output management, that the target output name is correct, that the transform is accepted, or that touch coordinates follow the transform.

## 2.6 Orientation service is not currently a continuous auto service

The checked-in unit `services/nuxel-orientation/systemd/nuxel-orientationd.service` currently has:

- `Type=oneshot`;
- `ExecStart=/usr/libexec/nuxel/nuxel-orientationd status`;
- `RemainAfterExit=yes`.

That runs a one-time status command and exits. `nuxel-orientationd watch <seconds>` is a bounded command, not a permanent sensor owner. Auto rotation needs a stable continuously running service or a proper sensor event subscription. Do not use a UI timer as the owner of rotation.

Create one long-running orientation owner, preferably an explicit daemon mode in `nuxel-orientationd` or a separate service module called by the same policy library. It must:

- start after the actual Wayland compositor/output is ready;
- restore the last selected mode safely at startup;
- monitor a verified sensor source only when the selected mode is auto;
- stop/reduce sensor activity in fixed modes;
- apply orientation changes with hysteresis/cooldown;
- publish state to Bridge/UI;
- handle sensor disappearance gracefully;
- recover if compositor/output restarts;
- shut down cleanly and restore a safe mode if required.

Do not start multiple watchers from Home, Settings and systemd. The service is the owner; UI clients send requests and read state.

## 2.7 Current rootfs builder omits orientation integration

In the supplied archive, `images/s10plus/build-phone-rootfs-inside-fedora.sh` contains no references to `orientation`, `nuxel-orientationd`, `orientation.json` or the orientation service unit. This is despite the Bridge expecting `/usr/libexec/nuxel/nuxel-orientationd` and the config README describing `/etc/nuxel/orientation/orientation.json`.

Verify whether another independently invoked provisioning/overlay process installs the service on the live phone. If not, add all orientation files to the canonical builder:

- executable `nuxel-orientationd`;
- `nuxel_orientation/` Python package (`policy.py`, `sensors.py`, `apply.py` and any new backend modules);
- `orientation.json` and `orientation.schema.json` at the configured paths;
- systemd unit for the real long-running service;
- any helper or polkit/permissions required for output transform operations;
- schema/test/install checks.

Ensure the Bridge environment/config and helper path match the installed path exactly. Add a clean-rootfs assertion that the executable, importable Python package, config, schema and enabled unit exist.

## 2.8 Active framebuffer source must be patched deliberately

The current S10+ builder compiles `tools/s10plus/a34/nuxel-wl-fb.c` as the installed framebuffer bridge. A newer `tools/s10plus/a67/nuxel-wl-fb.c` exists, but it is not automatically the active binary merely because its directory number is larger.

- Determine which exact `nuxel-wl-fb` source the active rootfs build compiles.
- Determine whether the running live binary matches that source via hashes/build IDs and deployment evidence.
- Make changes in the active source or intentionally update the builder to a newer source with a fully reviewed provenance/test migration.
- Never patch A67 and leave A34 as the installed source by accident.

The bridge is the single owner of `/dev/fb0`. It captures Wayland frames through `zwlr_screencopy_manager_v1` and presents them to the Samsung DECON/AMOLED path. Keep this one-owner invariant.

## 2.9 Output name/backend contradiction

The orientation config names output `DSI-1`. Earlier A53/A54 evidence reports the actual Phoc compositor output as `HEADLESS-1`, with no `wlr-randr` transform backend. `configs/s10plus/display/nuxel-s10plus-display.sh` also names `DSI-1`, but its comments describe a display-mode setup helper and may not represent the live output.

Query the real running compositor using the available Wayland protocol tools, compositor logs and the active session. Record:

- actual `wl_output` global and output name;
- current logical width/height;
- physical framebuffer width/height and virtual geometry;
- transform/scale if exposed;
- supported output-management protocol globals;
- whether Phoc/wlroots accepts a transform for the headless output;
- whether the `nuxel-wl-fb` capture dimensions follow the logical output dimensions after a transform;
- whether libinput/Phoc already remaps touch to transformed output coordinates.

Do not assume `DSI-1` or `HEADLESS-1` until verified on the actual handset.

## 2.10 Sensor hardware blocker already documented

The repository's A69 hardware-boundary document records:

- Broadcom BCM47752KUB1G sensor hub / SSP path;
- physical STM LSM6DSO accelerometer behind that hub;
- Samsung sensor class exposes an accelerometer object;
- `raw_data` reported `0,0,0`;
- logs reported the SSP subsystem down and command failures;
- IIO devices exposed timestamps but not usable raw X/Y/Z accelerometer channels or scale;
- BCM4775x sensor-hub firmware was not present in the inspected firmware tree;
- no compatible Samsung sensor-hub userspace daemon was installed;
- only the diagnostic/manual source was available to the orientation service;
- seven-mode policy tests passed, but Auto modes were blocked by missing real gravity readings.

Re-probe the actual device; do not blindly repeat the historic conclusion. The state may have changed. Use the existing diagnostics and inspect current kernel/userspace evidence.

Potential real sensor paths to evaluate:

1. IIO accelerometer channels with a readable scale and validated data.
2. `iio-sensor-proxy` only when it reports `HasAccelerometer=true` and current, changing orientations.
3. Samsung sensor-class or SSP event/command interface only if a supported and licensed firmware + protocol/userspace path exists.
4. A genuine kernel input event sensor source, if the driver exposes gravity/orientation events with verifiable changes.

A sensor node existing is not enough. Zero values, synthetic values, manual fixtures or cached boot data are not real sensor inputs. Do not mark any source `auto_capable` until it delivers live, changing, physically plausible readings.

If the SSP firmware is the blocker, establish provenance and licensing for any owner-supplied firmware; do not fetch random blobs or use an Android HAL binary as an unexplained black box. Do not flash a kernel in this mission.

---

# 3. ESTABLISH A HARDWARE / SOFTWARE BASELINE BEFORE EDITING

Create an evidence directory:

`docs/beta-finalization/live/evidence/pwnage-46000/`

Capture a baseline before any change.

## 3.1 Repository/build baseline

Record:

- current git branch, commit, dirty state and diff;
- source archive/current checkout revision;
- exact `build-phone-rootfs-inside-fedora.sh` display source path;
- current installed orientation helper, unit and configuration presence;
- hashes of active `/usr/lib/nuxel/nuxel-wl-fb`, orientation helper and Bridge files;
- actual PWA cache/service-worker version for Home and Settings;
- service graph for Phoc, Wayland, framebuffer bridge, input and orientation.

## 3.2 Live output/display baseline

Read-only diagnostics first:

- running compositor/session process and command line;
- Wayland display socket and user/session environment;
- output globals/names, mode, logical dimensions, scale and current transform;
- framebuffer `/dev/fb0` geometry/format/stride/virtual resolution via `FBIOGET_VSCREENINFO` and `FBIOGET_FSCREENINFO` where the existing diagnostic helper safely supports it;
- panel/backlight/DECON ownership and active `nuxel-wl-fb` PID;
- ensure exactly one active framebuffer writer;
- `wlr-randr` availability and actual output listing if supported;
- available Wayland output-management protocols;
- Phoc config and headless output creation path;
- native dock surface/output association and current bottom reserved area.

Do not probe by writing to the framebuffer or forcing a new mode during baseline collection.

## 3.3 Input/touch baseline

- identify actual touchscreen input device(s) and driver;
- determine input coordinate ranges, resolution, axis inversion/swap and physical panel dimensions;
- record the current libinput/Phoc device mapping and seat assignment;
- inspect the current `libnuxel-libinput-path.so` shim only for what it actually changes (it was added as a device-path compatibility shim; do not assume it performs calibration);
- confirm current touch points at four screen corners, four edge midpoints and centre;
- verify keyboard hitboxes and Home/dock buttons in native portrait;
- capture a touch diagnostic log without recording sensitive user content.

## 3.4 Orientation/sensor baseline

Run the current helper if installed, and the source-tree test harness locally:

```sh
nuxel-orientationd status --json
nuxel-orientationd modes --json
nuxel-orientationd selftest
nuxel-sensors-diag.sh watch accelerometer 20
```

If commands are not installed, do not report a successful baseline. Check the exact helper path and the rootfs omission above. Record per-source availability, failure reason and any readings. Do not run a `watch` loop indefinitely.

## 3.5 Notes feedback baseline

The Notes app stores the notes array with the Bridge key `nuxel-notes` and a localStorage fallback. Confirm the Bridge store is reachable and current Notes save works before relying on it. Record only the dedicated test note metadata; do not export all user notes to logs.

---

# 4. IMPLEMENT THE DISPLAY ROTATION PIPELINE — NOT CSS ROTATION

## 4.1 Required coordinate/display pipeline

The correct end-to-end path is:

**orientation policy → verified effective angle → Wayland output logical geometry/transform → screencopy frame → single framebuffer presenter → physical panel; and separately physical touch coordinates → inverse/associated transform → correct Wayland logical coordinates.**

Use the existing compositor/output transformation if it can perform this safely. Otherwise implement a coordinated presenter transform and input calibration that maintains the compositor's logical dimensions, CSS viewport and touch coordinates. A presentation-only bitmap rotation is incomplete if the logical viewport still claims portrait dimensions or if touches land at the wrong coordinates.

## 4.2 Backend selection

The existing `apply.py` attempts only `wlr-randr`. First repair executable detection, then determine whether the active Phoc/wlroots build exposes a supported output-management interface for its actual output.

Possible approaches to evaluate, in order of architectural fit:

1. Native wlroots output transform applied by the actual compositor to the active output, with the corresponding input transform handled by the compositor/libinput output association.
2. A supported Phoc configuration/control API for headless output transform and logical size, if the shipped Phoc version exposes it.
3. A coordinated Nuxel presenter transform in the active `nuxel-wl-fb` plus a correct logical output resize and touch-coordinate matrix owned by the input/compositor path.

Do not add a new separate compositor, replace Phoc, introduce a second display server, or write directly to `/dev/fb0` from a second helper. Do not assume `wlr-randr` can control a headless output just because the utility exists.

## 4.3 Rotated dimensions and buffer geometry

The panel is physically portrait scanout, reported as 1440×3040. Landscape logical content will have swapped dimensions (nominally 3040×1440) before being mapped to the portrait scanout. Verify actual output and capture dimensions on the handset; do not hardcode guessed dimensions if the running mode differs.

For each orientation:

- 0°: logical portrait geometry, native portrait scanout transform;
- 90°: landscape logical geometry, mapped to the physical portrait framebuffer through the calibrated inverse transform;
- 180°: reverse portrait geometry, correct vertical inversion;
- 270°: landscape logical geometry, opposite inverse transform.

The exact orientation/transform direction must be physically calibrated. The mapping in the existing JSON is a candidate, not an established truth.

If implementing pixel rotation in `nuxel-wl-fb`:

- preserve source pixel format, stride, alpha/color conversion and buffer bounds;
- use correct source/destination dimensions for quarter turns;
- swap axes for 90°/270°;
- avoid integer overflow and out-of-bounds reads/writes;
- account for physical framebuffer stride/padding and line length;
- preserve panel commit cadence and `FBIOPAN_DISPLAY`/DECON semantics already measured for this device;
- never call a full mode reset per frame;
- avoid excessive CPU cost; precompute mapping/row offsets or use efficient row/column traversals;
- keep screenshot/screencopy content and display presentation consistent;
- preserve source-frame hash/damage optimizations correctly across orientation changes.

If the compositor can perform the transform, prefer that over rotating the full captured image in the presenter, because the compositor can also update logical geometry and potentially route touch correctly. Verify this instead of assuming.

## 4.4 Viewport and application relayout

The user must see real portrait/landscape layout changes, not a sideways portrait page with a rotated framebuffer.

Verify that:

- `wl_output` logical width/height swap for landscape as appropriate;
- WebKitGTK viewport metrics update (`innerWidth`, `innerHeight`, `visualViewport`, CSS `orientation` media query);
- PWA safe-area insets/cutout mapping are correct;
- CSS layout reflows at the new aspect ratio;
- native GTK windows receive the new allocation and rotate/resize correctly;
- lockscreen clock and indicator rows reposition rather than merely rotate into the wrong physical edges;
- top bar and bottom navigation dock remain at their intended physical edges;
- touch keyboard/OSK reflows, remains usable and is not clipped;
- modal dialogs and QS panels reposition and remain reachable;
- screenshots and Gallery previews reflect what was actually displayed.

Do not patch each app with `transform: rotate(...)`; fix the output at the correct system layer.

## 4.5 Native dock and overlay surfaces

The active bottom dock is a native Wayland layer-shell surface (`tools/s10plus/a45/nuxel-navdock.c` in the supplied archive). It reserves/uses bottom-edge space and has touch actions for Back/Home/Tabs. Test whether its layer-shell anchor and exclusive zone follow the transformed output. If not, adapt it through the actual output/logical geometry API so the dock stays along the physical bottom edge in both portrait and landscape.

Also verify:

- lockhead and lockscreen background;
- status bar/safe zones;
- notification OSD;
- QS panel and long-press rotation menu;
- volume/power OSD;
- native application surfaces;
- on-screen keyboard;
- pointer/touch cursor if visible.

Do not leave overlays anchored to the wrong pre-rotation coordinates.

---

# 5. TOUCH INPUT TRANSFORM — MUST MATCH THE PIXELS

## 5.1 Non-negotiable requirement

Every rotation mode must leave touch aligned with the rendered UI. Rotated pixels with portrait touch coordinates are a failure and must automatically roll back.

Touch transform should preferably be handled by the compositor's output transform and its device-to-output association. If the implementation uses a presenter-side transform that the compositor does not know about, the input path must apply the matching coordinate transform before events reach the compositor. Keep a single source of truth for the same 0/90/180/270 transform.

## 5.2 Coordinate mapping

For a normalized touchscreen coordinate `(x, y)` in `[0,1] × [0,1]`, the conceptual rotation mappings (clockwise convention, subject to hardware calibration) are:

- 0°: `(x, y)`;
- 90°: `(1 - y, x)`;
- 180°: `(1 - x, 1 - y)`;
- 270°: `(y, 1 - x)`.

Do not copy these formulas into production without checking the input device's raw axis orientation, display-native mounting and compositor transform convention. The physical sensor/touch controller can be mounted rotated relative to the panel. Use the correct calibrated affine transform, including swap, inversion and scale where needed.

If the compositor manages transforms, let it own the coordinate mapping rather than applying the same transform again in a shim. Double-applying an inverse matrix is a common failure.

## 5.3 Required physical touch checks for every orientation

- Tap all four visible corners.
- Tap the centre.
- Tap four edge midpoints.
- Tap Back, Penguin Home and Tabs dock cells.
- Open QS and tap its close/back area and at least one tile.
- Open the Notes app, tap title/body and type a short test string.
- Open the keyboard and tap several keys near each edge.
- Scroll a Notes document.
- Verify a modal button is activated exactly where it appears.

Touch must not be mirrored, inverted, offset, rotated twice or clipped. Confirm multitouch/gesture/edge-swipe behavior as far as the hardware path supports it.

---

# 6. SENSOR PATH — REAL GRAVITY INPUT FOR AUTO MODES

## 6.1 Probe every supported source honestly

`services/nuxel-orientation/nuxel_orientation/sensors.py` currently supports:

- IIO accelerometer raw X/Y/Z channels with a readable scale;
- `iio-sensor-proxy` D-Bus `HasAccelerometer` and `AccelerometerOrientation`;
- a manual source for diagnostics/tests only.

Re-run live diagnostics and extend the source discovery if necessary. Evaluate only real hardware data:

- `/sys/bus/iio/devices/iio:device*/name`;
- readable `in_accel_x_raw`, `in_accel_y_raw`, `in_accel_z_raw` plus scale;
- `/sys/class/sensors/accelerometer_sensor`/gyro status where relevant;
- SSP/sensor-hub status/firmware error logs;
- `/dev/input/event*` sensor devices only if a real input protocol produces meaningful orientation events;
- `net.hadess.SensorProxy` only if the service reports a genuine accelerometer.

No node name, device tree compatible, directory or class alone proves data is live.

## 6.2 Historical sensor hub issue

Previous repository evidence described a Broadcom BCM47752KUB1G SSP hub with an STM LSM6DSO accelerometer. The physical sensor was enumerated, but the hub did not boot, sysfs raw values were all zero, IIO channels were unavailable, and firmware/userspace support was absent. This made all automatic modes honestly `sensor_unavailable`.

Re-verify. Do not assume the blocker was fixed by the existence of new config files. Do not fabricate gravity vectors from the current phone mode or use the manual sensor fixture in production.

## 6.3 Calibration procedure

Only after a real sensor source provides changing readings:

1. Record source identity, raw channels, scale, units, sampling interval and timestamp.
2. Hold the handset in natural portrait, stable on a flat table and screen facing owner.
3. Record stable gravity samples.
4. Rotate 90° clockwise into landscape and record.
5. Rotate 180° into reverse portrait and record.
6. Rotate 270° into reverse landscape and record.
7. Repeat the sequence at least twice.
8. Derive the sensor-to-display mount matrix using those real observations.
9. Derive/classify gravity reference vectors.
10. Verify that the classifier labels each pose correctly across repeated movements.
11. Test face-up/face-down/near-flat conditions and weak/ambiguous gravity.
12. Only then set `calibration_status` to `verified`.

Persist calibration with version/source/device metadata and a clear way to invalidate it when kernel/device/source changes.

## 6.4 Classifier behavior

The existing policy has hysteresis, debounce, cooldown and flat-gravity thresholds. Review their actual behavior with real samples. Requirements:

- stable orientation changes after an appropriate 300–800 ms settle window;
- no jitter/flapping near thresholds;
- ignore short transients/jerks;
- preserve last good pose when phone is flat or gravity direction is ambiguous;
- obey the selected mode's allowed set at every moment;
- do not rotate while sensor state is stale or invalid;
- handle sensor source disappearance and restart;
- never block the UI thread while reading sensors;
- no excessive polling in fixed/manual modes.

Use monotonic timestamps for hysteresis, cooldown and watchdogs.

## 6.5 Auto modes cannot be marked complete without physical sensor evidence

For `Auto`, `Auto (PT)` and `Auto (LS)`, the user must physically rotate the handset and see it follow. A mocked vector, a test fixture, a software slider or a UI state change is not an auto-rotation pass.

If the sensor hub still lacks firmware/protocol support, complete the manual rotation modes and all backend integration, then document the exact hardware prerequisite for automatic modes. Do not call the whole seven-mode task complete.

---

# 7. MODE SERVICE, BRIDGE CONTRACT AND ROOTFS INSTALLATION

## 7.1 One authoritative owner

Keep `policy.py` as the mode policy source. Keep one service/daemon as the owner of sensor monitoring, current effective orientation, applying transforms, rollback and state publication.

Home QS, Settings, `nuxelctl` and diagnostics are clients. They must not implement competing angle tables or start their own watcher loops.

## 7.2 Continuous daemon

Replace or extend the current oneshot unit with a properly managed long-running service. Requirements:

- `Type=simple` (or another justified service type for a real daemon);
- executable daemon mode with a bounded event/read loop;
- correct `After=` dependencies on Wayland/Phoc and display readiness;
- restart handling that does not repeatedly reset a working transform;
- user/group and write permissions limited to orientation state/runtime paths and the required transform API;
- no unnecessary root access if compositor/API permissions permit a user service;
- startup restoration of persisted mode and safe effective orientation;
- one service instance only;
- clean stop and restart semantics;
- persistent diagnostics and structured status.

The previous `ExecStart=... status` cannot provide continuous auto-rotation. Do not keep it as the only service behavior.

## 7.3 Bridge set semantics

Fix `OrientationConnector` and daemon CLI/RPC semantics so the normal UI `orientation.set` request actually attempts a safe transform. A successful persistence operation alone must not return a green “applied” result.

Recommended state shape (adapt names to repository conventions but keep equivalent separation):

```json
{
  "mode": "landscape",
  "mode_label": "Landscape",
  "effective_orientation": 90,
  "requested_orientation": 90,
  "allowed": [90],
  "sensor": {
    "available": false,
    "source": null,
    "reason": "fixed mode does not require a sensor"
  },
  "display": {
    "output": "actual-live-output-name",
    "logical_width": 3040,
    "logical_height": 1440,
    "physical_width": 1440,
    "physical_height": 3040,
    "transform": "calibrated-transform",
    "applied": true
  },
  "touch": {
    "transform_available": true,
    "verified": false
  },
  "trial": {
    "pending_confirmation": true,
    "deadline_monotonic_ms": 0
  },
  "last_error": null
}
```

This is an illustrative contract, not a requirement to use these exact field names or placeholder values. Never return fake dimensions or output names; populate from the actual device.

## 7.4 Rootfs builder integration

The supplied current build script contains no orientation installation references. Add the actual service/config/helper/package to `images/s10plus/build-phone-rootfs-inside-fedora.sh` if there is no other canonical build integration.

Install:

- `nuxel-orientationd` in the path expected by Bridge (or update Bridge to the canonical installed path);
- Python package modules;
- `/etc/nuxel/orientation/orientation.json`;
- `/etc/nuxel/orientation/orientation.schema.json`;
- `nuxel-orientationd.service` and required target symlinks;
- any required compositor helper or policy file;
- tests/build assertions validating imports and executable paths.

Do not ship a oneshot status unit while describing the feature as live auto-rotation.

---

# 8. SAFE TRANSFORM TRIAL, OWNER CONFIRMATION AND AUTOMATIC ROLLBACK

## 8.1 Why the existing 4-second rollback is unsuitable

The current config's `revert_after_ms` is 4000 ms. Four seconds is too short for a human to see a newly rotated screen, orient the phone, verify touch, open/continue Notes and type feedback.

Implement a controlled test transaction with a 60–90 second confirmation window. The exact default may be configurable, but it must be long enough for the required physical interaction and bounded enough to recover an unusable screen.

## 8.2 Transform trial state machine

Use a single transform transaction state machine such as:

```text
LAST_GOOD
  -> SNAPSHOT_PREVIOUS_DISPLAY_AND_TOUCH_STATE
  -> APPLY_CANDIDATE_DISPLAY_AND_INPUT_TRANSFORM
  -> VERIFY_COMPOSITOR_ACCEPTED
  -> WAIT_FOR_OWNER_NOTES_FEEDBACK
       -> YES/WORKS: COMMIT_AS_LAST_GOOD
       -> NO: ROLLBACK
       -> BLANK_SAVED_RESPONSE: ROLLBACK
       -> TIMEOUT: ROLLBACK
       -> DISPLAY_OR_INPUT_GUARD_FAILURE: ROLLBACK
  -> IDLE
```

Do not treat “wlr-randr returned zero” as owner confirmation. The owner must be able to interact with the actual rotated interface.

## 8.3 Independent rollback watchdog

- Watchdog is part of the service/host path and must not depend on the Python agent process or SSH connection remaining alive.
- Persist or hold the last-known-good display and touch transform with enough information to restore it.
- On service crash/restart, ensure pending trial cannot leave the screen in an unknown transform; restore last-good or safe portrait.
- On no confirmation, blank/failure or timeout, apply the exact previous transform and input mapping.
- Do not revert a previously committed good mode merely because another UI panel refreshes.
- If a touch/device safety signal or compositor error proves the output cannot be interacted with, rollback immediately.
- Test rollback with a deliberately invalid transform and a deliberately unconfirmed valid transform.

## 8.4 Owner confirmation protocol

The owner explicitly requested that the Notes app be the feedback channel. Implement and use it; do not substitute a terminal-only question.

### Dedicated feedback note

Use the existing Notes app and its persistent Bridge storage key `nuxel-notes`. Create one dedicated note only, with a unique run ID:

**Title:** `PWNAGE-46000 Rotation Test Feedback`

Initial body:

```text
PWNAGE-46000 ROTATION FEEDBACK
Run: <unique-run-id>

The agent will give one physical rotation test at a time.
Before each test, ensure the ANSWER line says WAITING.
When the requested display + touch behavior works correctly, replace WAITING with: yes (or works).
If anything is wrong, type: no. You may also delete WAITING and leave the answer blank to report failure.
Do not leave an old yes in place for a new test.

CURRENT TEST: not started
ANSWER: WAITING
NOTES: optional explanation of what did not line up
```

Do not put sensitive content in this note. Preserve every pre-existing note and note ID. Do not overwrite the user's open note or remove their data.

### How the agent reads feedback

The Notes source in the supplied archive (`pwa/nuxel-apps/notes/js/notes.js`) reads/writes a notes array through:

- Bridge `storage.read` with `{ key: 'nuxel-notes' }`;
- Bridge `storage.write` with `{ key: 'nuxel-notes', data: notes }`;
- localStorage fallback for offline recovery.

Use the authoritative Bridge-backed record when reachable. Locate the dedicated note by its unique ID, not by assuming it is the first note. Parse only the response field and `updatedAt` needed for feedback; do not dump other note content into logs.

Response rules:

- case-insensitive, trimmed `yes` or `works` → PASS for the current challenge;
- `no` → FAIL for the current challenge;
- an intentionally deleted/empty answer after the challenge started and after an observed Notes save/update → FAIL;
- unchanged `WAITING` → still waiting until the announced response deadline;
- unchanged/stale `yes` from a prior challenge → invalid; do not count it;
- Bridge unavailable or Notes save not observed → unknown/pending, not success.

Before each new trial, re-arm the answer to `WAITING` and confirm the baseline has been saved. If the Notes editor cannot safely accept a programmatic update while open, ask the owner to reset the answer to `WAITING` before the next challenge. Never overwrite active unsaved editor text. Do not falsely interpret an empty note before the challenge as an intentional failure; compare `updatedAt`/revision against the challenge baseline.

If the owner types `no`, rollback immediately and start diagnosis. If the owner leaves the answer blank after deleting the marker and the save is observed, rollback and treat as failure. If no response arrives by the announced 60–90 second deadline, rollback and record `NO_FEEDBACK_TIMEOUT`; do not mark success.

### Test presentation

Give exactly one actionable physical test at a time. For every challenge tell the owner:

- exact mode label and current effective orientation;
- how to hold/rotate the handset;
- what must rotate or stay fixed;
- what screen/application should remain open;
- which touch points to check;
- when to type `yes`/`works`, `no` or leave blank;
- that failure/timeout automatically returns to last-good orientation.

Do not issue five simultaneous tests and then ask for one vague yes/no. The Notes answer must be bound to one named test ID.

---

# 9. ITERATIVE REPAIR LOOP — THE CORE OF THIS MISSION

The owner expressly wants the agent to keep iterating until it works. Follow this procedure for every physical failure:

1. Record the current test ID, policy mode, physical pose, expected angle, effective angle, output transform, logical output size, framebuffer geometry, touch matrix, sensor reading/source and Notes answer.
2. Capture only relevant logs from the orientation service, Bridge, Phoc, `nuxel-wl-fb` and input stack. Do not flood the user with unrelated logs.
3. Classify the defect into one or more layers:
   - mode-key/label/policy mismatch;
   - Bridge does not issue apply;
   - orientation helper absent or not installed;
   - daemon not running/only oneshot;
   - wrong output name/backend;
   - compositor transform unsupported/rejected;
   - wrong transform direction;
   - logical output dimensions not swapped;
   - presenter framebuffer rotation/stride/pixel mapping;
   - touch coordinate matrix missing/wrong/double-applied;
   - WebKit viewport/media-query not updating;
   - native dock/OSK/overlay anchoring incorrect;
   - sensor raw data/scale/mount matrix/classification incorrect;
   - hysteresis/flat-pose policy incorrect;
   - service state not synchronized to QS/Settings.
4. Make the smallest coherent source change that addresses the diagnosed layer. Do not randomly change multiple matrices/angles at once; it makes physical cause/effect ambiguous.
5. Run unit tests, policy tests, transform math tests, service tests, packaging checks and relevant UI tests locally.
6. Build the exact active ARM64 binary/source path. Confirm the rootfs builder installs the changed source and that the installed hash matches the build artifact.
7. Deploy a staged delta over the existing configured Wi-Fi SSH path if available. Back up active files and config first. Restart only the necessary service(s). Keep the framebuffer owner and SSH/network path safe.
8. Verify machine-readable status before asking the owner. A machine check must prove the desired transform is applied, the daemon is alive, touch transform is enabled and no error is active. It still does not replace the owner test.
9. Open/leave Notes on the feedback note and issue the next exact physical challenge.
10. Read `yes`/`works`, `no` or intentional blank from the saved note. Commit only on a current affirmative response. Otherwise rollback and repeat.

Do not stop at an arbitrary three attempts. Maintain an iteration log. If a problem requires firmware/hardware/kernel support not available in the repository, exhaust legitimate userspace alternatives and document the exact blocker, evidence and owner-provided artifact required. Do not endlessly ask the owner to repeat a test without changing code or obtaining new diagnostic evidence.

---

# 10. TEST MATRIX — ALL SEVEN MODES

The owner should test in this order. Keep Notes foreground/open where possible so feedback stays accessible.

## 10.1 Fixed manual modes first

### Test M1 — Portrait

- Select `Portrait`.
- Screen is native portrait and text is upright.
- Rotate the handset clockwise to landscape, then upside-down, then opposite landscape.
- The display content must remain fixed in portrait; the phone must not auto-rotate.
- Test all four touch corners, dock buttons, one QS tile and Notes title/body typing.
- Return the phone to a comfortable pose and submit the Notes answer.

### Test M2 — Landscape

- Select `Landscape`.
- Screen switches to the chosen normal landscape orientation immediately.
- Logical viewport is landscape, text is upright, dock is on the physical bottom edge, keyboard is correctly placed.
- Turn the physical handset to portrait and reverse landscape; the screen must remain in the selected landscape mode.
- Test four corners, dock, QS and Notes typing.

### Test M3 — RPortrait

- Select `RPortrait`.
- Screen is rotated 180° relative to native portrait and the content remains upright to the owner holding the phone in the reverse portrait test pose.
- Verify top/bottom positions, touch corners, dock mapping, keyboard and Notes typing.
- Tilt the handset to landscape; selected orientation must remain locked to RPortrait.

### Test M4 — RLandscape

- Select `RLandscape`.
- Screen is the opposite landscape direction from `Landscape`.
- Verify UI text is upright in the reverse landscape hold, the logical viewport is landscape, and touch mapping is not mirrored.
- Check all four corners, dock buttons, QS and Notes typing.
- Move phone back to portrait; screen remains fixed RLandscape.

For each fixed mode, sensor availability is irrelevant. If a fixed mode fails when the sensor is unavailable, the bug is in display/apply/input packaging or output transforms, not gravity classification.

## 10.2 Auto modes

Only test after a genuine accelerometer source is live and calibration is verified.

### Test A1 — Auto

- Select `Auto`.
- Hold in normal portrait: screen is portrait (`0°`).
- Rotate clockwise to normal landscape: screen follows to `90°` after stable settle.
- Rotate upside-down: screen follows to `180°`.
- Rotate to the opposite landscape: screen follows to `270°`.
- Return to normal portrait.
- Lay flat/face-up for several seconds: screen stays on the last stable allowed orientation and does not flap.
- Tilt slowly around threshold: no repeated oscillation.
- Confirm every switch keeps touch and Notes editing aligned.

### Test A2 — Auto (PT)

- Select `Auto (PT)` while holding normal portrait.
- Rotate to reverse portrait: it must switch to `180°`.
- Rotate to either landscape pose: it must remain in the last permitted portrait orientation; never show landscape.
- Return upright: it switches to `0°`.
- Lay flat: hold last good permitted portrait angle.

### Test A3 — Auto (LS)

- Select `Auto (LS)`.
- Enter the chosen normal landscape pose: it must be in `90°`.
- Rotate to the opposite landscape pose: it must switch to `270°`.
- Rotate to normal/reverse portrait: it must remain in the last permitted landscape orientation; never enter portrait.
- Lay flat: hold last good permitted landscape angle.

## 10.3 Mode-switch and restart tests

- Change from each fixed mode into each relevant auto mode and vice versa.
- Verify the first effective angle always belongs to the new mode's allowed list.
- If an auto mode has no valid sensor, show blocked/unavailable instead of claiming it has started.
- Verify selected mode persists across Home restart, Bridge restart, orientation service restart and normal device reboot when owner authorizes it.
- On service start, restore a safe transform before presenting the Home screen where feasible.
- If saved mode is corrupt/unknown, fall back to Portrait and log migration; never choose a random transform.

---

# 11. AUTOMATED TESTS AND TEST COVERAGE

The archive already contains tests under `services/nuxel-orientation/tests/`:

- `test_policy.py`
- `test_sensors.py`
- `test_apply.py`
- `test_daemon.py`

The current tests cover policy, mode lists, persistence, a dry-run and fake transform backend behavior. Extend them to cover actual new service/apply/rollback contracts. Passing offline tests is necessary, not sufficient.

## 11.1 Policy/mode tests

- Exactly seven stable keys.
- Exactly seven exact UI labels.
- Correct `allowed` sets for all modes.
- Manual modes do not need sensor.
- Auto modes require a real auto-capable source.
- Auto-PT never emits 90/270.
- Auto-LS never emits 0/180.
- Switching into a restricted auto mode chooses a valid initial pose immediately.
- Flat/ambiguous input holds last allowed orientation.
- Invalid sensor values do not change effective orientation.
- Legacy underscore aliases migrate once and remain canonical.
- State corruption defaults safely to Portrait.

## 11.2 Transform math tests

Test pure mapping functions independent of hardware:

- every degree to compositor transform mapping;
- source/destination dimensions for quarter turns;
- pixel coordinate mapping for corners and centres;
- touch affine matrix for all four orientations;
- inverse relationship between display output transform and touch input transform;
- exactly one transform in each direction (no double application);
- landscape dimensions swap;
- framebuffer stride/padding handled correctly;
- bounds/overflow guards;
- correct alpha/color format handling if any conversion is reused.

Use known asymmetric test patterns labelled TOP/LEFT/RIGHT/BOTTOM and unique colors at each corner. A symmetric test image can conceal a mirrored or inverted transform.

## 11.3 Apply/backend tests

- `wlr-randr` binary discovery using `shutil.which` or equivalent;
- missing utility;
- utility present but output missing;
- headless output not supported;
- compositor rejects transform;
- transform succeeds;
- command timeout;
- stale output disappears/reappears;
- transform rollback restores previous output and touch state;
- service restart with pending transaction;
- no `applied=true` unless actual backend confirms;
- no `touch.verified=true` from a display-only result.

## 11.4 Daemon/service tests

- long-running process starts once and continues;
- no second watcher instance;
- auto sampling only in auto modes;
- manual modes stop or idle sensor sampling;
- sensor loss doesn't cause a crash/flapping;
- compositor restarts and service reapplies last-good state;
- command Bridge sets mode and requests application;
- state is atomically persisted;
- timeout watchdog rolls back after missed/negative feedback;
- explicit yes commits;
- no rolls back;
- intentional empty response saved after test begins rolls back;
- stale yes does not commit the next trial;
- no Bridge/SSH dependency for watchdog rollback.

## 11.5 Packaging/build tests

- clean S10+ rootfs includes orientation executable;
- Python package import works at the installed path;
- config/schema and service unit are installed;
- service is enabled or started by the correct target;
- Bridge helper path exists and is executable;
- installed hashes correspond to compiled/source artifacts;
- builder does not silently omit orientation files;
- active `nuxel-wl-fb` source is the one changed/tested.

## 11.6 UI tests

- QS Rotate tile displays exact labels and selected mode;
- long-press menu lists all seven in requested order;
- Settings radio values map to canonical IDs;
- current state refresh after Bridge event;
- error/unavailable display is truthful;
- tap toggle semantics are clear and do not silently jump out of a user-selected mode unexpectedly;
- no duplicate event handler/poller on repeated QS/Settings open;
- orientation changes cause the expected viewport and layout updates.

Run the existing relevant tests and all new tests. Add a consolidated `services/nuxel-orientation/tests/run-tests.sh` or integrate with the repository's existing test runner; do not leave the critical service tests as manually discovered scripts.

---

# 12. PERFORMANCE, STABILITY AND VISUAL QUALITY

The S10+ display path uses software rendering and a shared-memory screencopy/presentation bridge. Keep rotation efficient.

- Do not allocate a fresh full-screen multi-megabyte buffer for every frame if a reusable buffer is practical and safe.
- Recompute orientation mapping only when the transform changes, not per pixel/per input event.
- If presenter-side rotation is required, use a bounded efficient row/column mapping. Measure frame time and CPU before/after.
- Preserve the existing panel presentation cadence and commit behavior.
- Avoid starting high-frequency sensor polls in fixed modes.
- Use event-driven sensor notifications if a legitimate source provides them; otherwise use the configured conservative interval.
- Keep hysteresis/cooldown and do not debounce so heavily that user rotation feels sluggish.
- On transform changes, invalidate source-frame hashes/caches so the new frame is actually committed even if the source capture pixels are otherwise identical.
- Avoid CSS transforms on the whole document as a substitute for a system output change.
- Do not introduce per-app special-case rotation unless an app has a documented fixed-orientation requirement and the owner approves.
- Record before/after presentation time, effective rotation latency, touch latency, CPU usage and dropped/late frames where measurable.

Target a stable 30 FPS presentation budget if the current bridge can sustain it, but do not claim the UI can render above the actual measured panel/bridge rate. Rotation itself should settle within approximately 300–800 ms after a stable auto sensor transition, without visible repeated oscillation.

---

# 13. UI REQUIREMENTS — QUICK SETTINGS AND SETTINGS

## 13.1 Quick Settings

- Keep Rotate tile in the existing QS grid.
- Display the current exact label: `Auto`, `Auto (PT)`, `Auto (LS)`, `Portrait`, `Landscape`, `RPortrait`, `RLandscape`.
- Long-press menu lists all seven, in the specified order.
- Selecting a mode shows pending state until the daemon responds.
- After response, display selected policy, effective angle and truthful sensor/backend status.
- On transform failure, display `Rotation not applied` plus reason; do not show a success toast.
- When trial confirmation is pending, show a clear temporary confirmation state with rollback deadline.
- Do not let a repeated click create overlapping transform trials.
- Avoid the existing tap shortcut forcing Portrait/Auto if it would unexpectedly override `Auto (PT)`, `Auto (LS)`, Landscape, RPortrait or RLandscape. Either make tap cycle clearly through the seven modes or keep tap as a simple rotation-lock toggle only if its effect is explicit and consistent. The long-press selector remains the full mode selection path.

## 13.2 Settings Display panel

Use exact seven labels. Keep canonical mode IDs in the API. Show separate fields for:

- selected mode;
- effective orientation;
- sensor availability and source;
- sensor calibration;
- output transform backend and result;
- touch transform status;
- safe trial/rollback state;
- latest blocker.

If mode persistence succeeds but compositor transform fails, show the failure. Avoid current wording that can make a user think physical rotation is working just because the mode is selected.

## 13.3 Lock screen and other surfaces

Check the lockscreen on all modes. It must re-layout with the output orientation. If it intentionally remains portrait for a specific boot/recovery safety reason, document that exception and test lock/unlock touch; do not let it become accidentally sideways or clipped. The standard requirement is that the selected system orientation is respected consistently after unlock and on the lockscreen.

---

# 14. NOTES APP — HUMAN-IN-THE-LOOP FEEDBACK IMPLEMENTATION

## 14.1 Preserve user data

Use the existing Notes app; do not create a second notes database. Do not delete, truncate, reorder or rewrite unrelated notes. Preserve current note IDs, titles, bodies and timestamps except for the dedicated test entry.

## 14.2 Create a dedicated test note

Create exactly one dedicated note through the existing Bridge storage contract if possible. Use an ID unique to this run and title:

`PWNAGE-46000 Rotation Test Feedback`

Use this body as the initial content:

```text
PWNAGE-46000 ROTATION FEEDBACK
Run ID: <generated-unique-id>

The agent will ask one physical test at a time.
Keep this note open while testing.
Before each test, make sure ANSWER is WAITING.
When the displayed orientation AND touch controls work correctly, replace WAITING with: yes (or works).
If any part fails, type: no. You may also delete WAITING and leave the answer empty to report failure.
Do not leave an old yes for a new test.

CURRENT TEST: WAITING FOR AGENT
ANSWER: WAITING
OPTIONAL DETAILS:
```

If the Notes app is already open, tell the owner to open this new note and keep it active. Do not force-close Notes or discard unsaved content.

## 14.3 Read the feedback safely

The Notes app in this archive uses:

- Bridge namespace `storage`, verb `read`, key `nuxel-notes`;
- Bridge namespace `storage`, verb `write`, key `nuxel-notes`, complete notes array;
- localStorage fallback with the same key.

The app autosaves edits after about one second. The agent must use the Bridge-backed store for its decision if it is available, and inspect only the feedback note. Check that the write has completed before deciding.

Response rules:

| Saved answer | Meaning |
|---|---|
| `yes` / `works` (case-insensitive, trimmed) | Current named physical test passed; commit trial. |
| `no` | Current test failed; rollback and diagnose. |
| Empty answer after user removed `WAITING` and the note `updatedAt` advanced after the challenge baseline | Failure; rollback. |
| `WAITING` unchanged | Pending; keep safe trial window open until timeout. |
| Old `yes` not changed for current challenge | Stale; never count it. |
| Bridge/Notes unavailable or save not confirmed | Unknown; do not commit. |

At the beginning of each test, record the note revision/`updatedAt` and current response. The answer must be re-armed to `WAITING` for each new test. If the agent cannot update the note without risking an editor conflict, ask the owner to do this manually and wait until the Bridge store shows it. Do not write a new body over an active unsaved Notes editor.

If the user leaves the response blank, the agent must distinguish an intentionally saved blank response from no response yet. Use note revision/timestamp, challenge start time and the `WAITING` sentinel. Never call a missing response a pass.

## 14.4 Notes test note is not a telemetry dump

Do not log the full user's Notes array or unrelated note bodies. Do not send note content anywhere off-device. Read only the note ID/title/body/status needed for the explicit rotation test. Keep optional owner comments in the note private and out of build logs.

---

# 15. PHYSICAL ACCEPTANCE SCRIPT — EXACT OWNER PROMPTS

After the first implementation passes local tests and the display rollback safety check, begin owner testing. Keep the Notes app open on the feedback note. Ask one test at a time.

Use the following sequence:

1. **Portrait lock test:** select Portrait, tilt the phone to all other physical poses, ensure the screen remains normal portrait, touch corners/dock, type in Notes.
2. **Landscape lock test:** select Landscape, verify normal landscape layout, touch corners/dock/keyboard and type in Notes; tilt the phone back to portrait and ensure the content does not rotate.
3. **Reverse portrait lock test:** select RPortrait and verify reverse portrait orientation and aligned touch/Notes entry.
4. **Reverse landscape lock test:** select RLandscape and verify the opposite landscape direction, aligned touch and Notes entry.
5. **Auto full test:** only if live sensor readings/calibration are verified; follow normal portrait → landscape → reverse portrait → opposite landscape → normal portrait; ensure every switch follows and touch remains correct.
6. **Auto (PT) test:** normal portrait → reverse portrait → landscape hold (must not change from allowed portrait) → normal portrait.
7. **Auto (LS) test:** normal landscape → reverse landscape → portrait hold (must not change from allowed landscape) → normal landscape.
8. **Flat pose/hysteresis test:** in each auto mode, lay the phone flat/face-up, wait, then tilt slowly; no flapping or uncommanded orientation.
9. **Cross-surface test:** check lockscreen, Home, QS, Settings, Notes, native dock, OSK and a native app where available.
10. **Persistence/recovery test:** switch mode, restart Home/Bridge/orientation service safely, verify state restores. Reboot only if genuinely required and owner-approved through normal safe operation.

For each individual test the agent must explicitly state:

- the exact mode;
- the physical orientation to hold;
- the expected direction of text and panel layout;
- what to touch/type;
- how to answer in Notes;
- that a `no`, saved blank or timeout automatically restores last-good.

---

# 16. FAIL-SAFE, RECOVERY AND DEVICE SAFETY

- No kernel flashing, Heimdall, Odin, fastboot, bootloader, recovery/download entry, partition writes, `dd` to block devices, forced reboot or sysrq reboot.
- No second process may open/write `/dev/fb0` as a display owner. The existing `nuxel-wl-fb` remains the only framebuffer writer.
- The orientation daemon must not kill Phoc, WebKit, native dock or input services as a shortcut.
- Do not apply a candidate output transform without a saved last-good transform and a tested rollback watchdog.
- Do not permanently change panel timings/DECON mode per frame; preserve the measured framebuffer commit process.
- Do not disable touch or switch input device ownership to make a visual test pass.
- Do not use an unverified firmware blob, kernel binary or random Android HAL for the sensor hub.
- Do not claim touch verified from a compositor command exit code; physical touch owner test is required.
- Do not claim auto rotation verified using simulated sensor inputs.
- Do not assume the phone is reachable over a guessed IP. Use the configured Wi-Fi SSH target, and preserve network/USB console access.
- Before any live change, snapshot config/state and backup affected binaries/configs. Use staged install and atomic replacement where practical.
- If a test makes the display or touch unusable, let the local watchdog restore last-good. Do not force a remote reboot or ask the owner to blindly tap.

---

# 17. REQUIRED EVIDENCE AND DELIVERABLES

Create/update:

1. `docs/beta-finalization/live/PWNAGE-46000-TODO.md` — all tasks, exact source paths, states, dependencies, owner tests, blockers and evidence pointers.
2. `docs/beta-finalization/live/evidence/pwnage-46000/` with:
   - `baseline/` output/sensor/input/service/build state;
   - `iterations/` numbered per failure/fix/deploy/owner response;
   - `screenshots/` safe screen captures of each orientation/mode;
   - `touch/` touch-corner calibration and confirmation logs;
   - `sensor/` raw samples/source provenance/mount matrix verification;
   - `build/` active ARM64 build hashes and rootfs contents;
   - `deployment/` staged install, service restart and rollback record;
   - `owner-feedback/` only the dedicated test note statuses/test IDs, not other Notes content.
3. Updated active source for orientation policy/daemon/apply backend/Bridge/UI and, if needed, the actual active `nuxel-wl-fb` source and touch-transform path.
4. Updated systemd unit, rootfs builder, installed config/schema and tests.
5. PWA cache/version updates for changed QS/Settings assets.
6. A machine-readable test report with exact counts and failure reasons.
7. A final report with:
   - confirmed root causes;
   - files changed;
   - backend path selected and why;
   - exact output/transform/dimension mapping;
   - touch calibration mapping;
   - sensor source and calibration status;
   - all seven mode results;
   - each owner response (`yes`/`works`, `no`, blank/timeout) with challenge ID;
   - tests run and exact PASS/FAIL/SKIP counts;
   - before/after rotation latency and frame performance;
   - any genuine hardware blocker and exact required firmware/kernel/userspace artifact;
   - deployment hashes and rollback instructions.

Do not label the whole mission `DONE` if only manual modes pass and auto remains sensor-blocked. Use a precise result such as `MANUAL_ROTATION_PASS / AUTO_BLOCKED_SENSOR_HARDWARE` when that is the truth.

---

# 18. FINAL DEFINITION OF DONE

## Policy and UI

- [ ] Exactly seven modes are present.
- [ ] Labels exactly match Auto, Auto (PT), Auto (LS), Portrait, Landscape, RPortrait, RLandscape.
- [ ] Stable canonical keys and legacy migration work.
- [ ] QS and Settings show the same selected mode and effective orientation.
- [ ] Mode set reports actual apply status, not only preference persistence.

## Display and touch

- [ ] Manual Portrait, Landscape, RPortrait and RLandscape physically rotate the panel/content correctly.
- [ ] Landscape logical dimensions/viewport are correct and swap appropriately.
- [ ] Touch transform matches all four display rotations.
- [ ] Touch corners, keyboard, dock buttons, QS, modal controls and Notes text entry work in every fixed orientation.
- [ ] Lock screen, Home, native dock, app windows, Settings, Notes and OSK remain usable.
- [ ] Single `/dev/fb0` owner remains intact.
- [ ] Rollback watchdog restores last-good on `no`, saved blank, timeout or input/display failure.

## Auto orientation

- [ ] A live sensor source supplies real gravity/orientation data.
- [ ] Sensor mount matrix and reference vectors are physically calibrated and marked verified.
- [ ] Auto follows all four poses.
- [ ] Auto (PT) follows only 0/180 and rejects both landscape poses.
- [ ] Auto (LS) follows only 90/270 and rejects both portrait poses.
- [ ] Flat/ambiguous poses hold last-good; no flapping.
- [ ] Continuous service actually runs at boot and is not a oneshot status command.
- [ ] If the sensor hub remains genuinely unavailable, auto modes are explicitly blocked and the exact firmware/protocol/kernel dependency is documented; no fake success.

## Feedback and iteration

- [ ] Dedicated Notes test feedback note exists without altering existing notes.
- [ ] Agent can read only the dedicated note using the Bridge-backed store.
- [ ] `yes`/`works` from the current challenge commits the trial.
- [ ] `no` or a saved blank response rolls it back and triggers diagnosis.
- [ ] A stale `yes` is never reused for a later test.
- [ ] No response times out and safely rolls back.
- [ ] Failed physical tests trigger code diagnosis, a new tested fix and another owner test—not a repeated request with no source change.
- [ ] Iteration continues until every achievable test passes or a precise external blocker is proven.

## Build and delivery

- [ ] Active ARM64 image includes the orientation helper, Python modules, config/schema and continuous systemd service.
- [ ] Rootfs builder and live binary hashes match the source being tested.
- [ ] Existing relevant tests plus new tests pass.
- [ ] All owner-confirmed tests are recorded with mode, pose, challenge ID and feedback.
- [ ] Safe deployment/rollback and final blocker matrix are documented.

**PWNAGE-46000 is complete only when the physical phone rotates correctly, the touch surface remains aligned, the Notes feedback confirms each owner test, and the service/build path reproduces the behavior after restart. A menu selection, persisted angle, CSS transform, mocked sensor sample or successful unit test is not physical rotation.**

🐧 **NUXEL — ROTATE THE DISPLAY. KEEP THE TOUCH. MAKE IT REAL.**
