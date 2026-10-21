# 🐧🔥 NUXEL A49 — OPERATION PENGUIN GYRO + BIG SCREEN + TACTILE KEYS

## IMPLEMENTATION-READY ENGINEERING MISSION — SIX ROTATION MODES, TRUE SENSOR BRING-UP, USB-C HDMI, CASTING, KEYBOARD HAPTICS

**Executor:** Senior Linux ARM64 / Samsung Exynos engineer; preferred model DeepSeek-v4-pro-thinking or equivalent.  
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, Fedora 43 ARM64, vendor Linux 4.14.x, Phoc/Wayland, WebKitGTK and current Nuxel Home.  
**Delivery:** Implement code, tests, real device integration, safe live USB deployment, owner acceptance, documented findings, PR-ready commits.  
**Safety:** NO FLASHING, NO RAW PARTITION WRITES, NO BOOT/RECOVERY/KERNEL REPLACEMENT, NO UNAPPROVED REBOOTS, NO UNVERIFIED LOSS OF LIVE USB RECOVERY.

## MISSION

Implement, not simulate, all six user-selectable orientation modes and a reliable Quick Settings/Settings integration; bring up wired USB-C external display output where supported by the *actual Nuxel kernel/display drivers*; implement the strongest real wireless casting method supported by Wi-Fi, display capture and encoding, with honest capability checks; and enable subtle reliable haptic feedback on the *currently working single native keyboard*, with on/off and intensity settings persisted across reboot.

**Protect the working system.** The S10+ currently demonstrates a custom penguin lockscreen and drag handle, active Nuxel launcher, native keyboard, navigation dock, Wi-Fi discovery, USB console, and carefully chosen pixel-art assets. Preserve lockscreen unlock, navigation, battery/metrics paths, input focus, display refresh, dock BG1/BG2 and session stability. Do not create new conflicting input daemons, rotation loops, display stacks, keyboard overlays or vibrator owners.

### Known repository entry points (from previous v0.6.3-beta artifact; reconfirm in CURRENT checkout)

- `configs/nuxel/sensors/sensors.json`, `configs/nuxel/sensors/README.md`: sensor capability manifest; hardware presence ≠ readable sensor values.
- `tools/s10plus/a33/nuxel-sensors-diag.sh`: IIO/input/sensor-hub discovery; `status`, `read`, `watch`, `selftest`.
- `pwa/nuxel-home/js/qs.js`: Quick Settings already has a `rotate` boolean/tile (`qs-rotate`); do not assume this is backed by actual orientation control.
- `configs/s10plus/display/nuxel-s10plus-display.sh`: existing device-specific display configuration.
- `configs/nuxel/keyboard/keyboard.json`: keyboard preferences, including `keyboard.haptics`; in older snapshots the provider is `stevia`/Phoc text-input v3; inspect the **actual currently working** keyboard after A45/A47 instead of reverting to an old implementation.
- `configs/nuxel/haptics/{haptics.json,settings.json,bridge.json,README.md}`: shared haptic policy and gated bridge. `tools/s10plus/a33/nuxel-haptics-{diag.sh,bridge.py}`: actuator discovery and event gateway. Do not add direct unsafe actuator writers in WebKit.
- `services/nuxel-bridge/src/bridge.py`: existing privileged system/UI API boundary. Search actual current bridge handlers before extending.
- Search present Home/Settings implementation, app registry, Wayland host process, compositor start scripts, systemd units, rootfs builder, live USB installer and current per-device overlay.

**These paths are evidence from an older archived tree, not proof of today's running image.** First enumerate current files and deployed services; record differences.

---

## PHASE 0 — NON-DESTRUCTIVE BASELINE AND RECOVERY

1. `git status`, branch, commit, diff; inventory existing work in progress. Never reset or overwrite someone else's changes.
2. Identify device from `/proc/device-tree/model`/compatible, `uname -a`, OS release, compositor version, Wayland display, active Nuxel services and rootfs revision. Do not assume the archived image matches the phone.
3. Verify live USB console and a tested recovery path independently of the graphical display; capture a backup of affected configs, binaries, assets, units and relevant system state off-device, with SHA-256, then record rollback commands.
4. Record `journalctl`, `dmesg` excerpts, input devices, DRM outputs, USB-C/PD driver capabilities, haptic node status, power and idle resource figures, lockscreen/keyboard behavior before changing anything.
5. Establish short milestone commits and a persistent PASS / PARTIAL / BLOCKED ledger. Do not count mocks or presence of files as hardware success.
6. Use small safe user-space changes first. Anything requiring a boot-critical kernel/device-tree change must be analyzed offline and explicitly reported as a blocked independent follow-up; never silently flash.

## PHASE 1 — ACTUAL SENSOR BRING-UP AND SENSOR COORDINATES

Do NOT assume the gyroscope is what performs static auto-rotation: **gravity from the accelerometer** normally determines portrait versus landscape, while gyro readings can improve responsiveness/filtering. Identify readable accelerometer channels *first*.

Inventory `/sys/bus/iio/devices`, `/dev/iio:*`, `/proc/bus/input/devices`, `evtest`/`libinput`-appropriate devices, vendor Samsung sensor-hub (`ssp_context`, `sensorhub`, etc.), driver/module status, user/group permissions, and rate units/scales. Run the existing bounded `nuxel-sensors-diag.sh` checks and inspect `dmesg` for initialization errors. Test with the owner deliberately tilting/rotating the actual phone. Collect X/Y/Z changes, timestamp, units and sensor identity for normal, upside-down, left, right, face-up/face-down; do not fabricate data if only group sensor-hub events are exposed.

Investigate `iio-sensor-proxy` and its D-Bus `net.hadess.SensorProxy` (`HasAccelerometer`, `AccelerometerOrientation`, `ClaimAccelerometer`, `ReleaseAccelerometer`). If installed and functional, use its events; `monitor-sensor` is useful for verification. If incompatible with Samsung's vendor sensor hub, implement a single minimal Nuxel sensor-adapter service that decodes a **verified** sensor source, rather than pretending generic IIO nodes exist.

Derive and record the S10+ **mount matrix** and orientation convention (display-native portrait vs physical axes), calibrating from actual device motion. Avoid confusing camera/device sensor axes and display coordinates. Verify the four discrete orientations; when flat, preserve the last good orientation rather than randomly flipping. If gyro is present, measure genuine angular rate and distinguish it from acceleration or synthetic rotation. Bound sampling and stop sensor subscription while display is off/locked when appropriate; verify resume, hot restart, and battery impact.

**Gate:** Four physical poses produce unambiguous raw readings and a validated orientation state, or provide an exact evidence-based sensor/driver blocker and continue with independent work.

## PHASE 2 — SIX AND ONLY SIX ROTATION MODES

Define ONE authoritative policy service and persist mode in a shared config/state model; backend current effective orientation is distinct from selected user policy:

| User-facing mode | Allowed orientations | Rule |
|---|---|---|
| `Portrait` | 0° | Forced normal portrait |
| `Reverse portrait` | 180° | Forced upside-down portrait |
| `Landscape` | 90° | Forced first landscape direction; verify mapping on S10+ |
| `Reverse landscape` | 270° | Forced opposite landscape direction |
| `Auto` | 0°, 90°, 180°, 270° | Sensor-based, all four |
| `Auto portrait` | 0°, 180° | Sensor-based, never rotates into landscape |
| `Auto landscape` | 90°, 270° | Sensor-based, never rotates into portrait |

There are **seven named entries if treating all four fixed positions plus all three auto policies**; implement all seven exactly as listed. The owner's phrase “six modes” is a count mismatch: do not omit `Reverse portrait` or either restricted-auto mode to satisfy the number six. Explicitly document seven modes and show all seven choices.

Policy rules: persist across process restart/reboot; prefer `Portrait` as safe initial default if no preference exists; optionally remember last effective orientation of auto modes; switching into Auto portrait/landscape from a disallowed posture chooses a legal initial position immediately (last permitted orientation or sensor-consistent choice); never leave orientation outside the selected allowed set. Add hysteresis/cooldown/debounce (~300–800 ms candidate, tune physically); reject weak/flat ambiguous gravity readings; protect against sensor noise and fast flapping; avoid long busy polling and duplicated subscriptions. Manual modes must work even if accelerometer/gyro is unavailable; restricted auto modes must honestly indicate `sensor unavailable`.

**Avoid rotated screenshots that do not correspond to rotated touch.** Rotating pixels alone is not acceptable.

## PHASE 3 — REAL PHOC/WAYLAND OUTPUT ROTATION AND TOUCH MAPPING

Identify compositor support for output management / output transforms (e.g., `zwlr_output_manager_v1`, compositor-native APIs, `wlr-randr` if genuinely compatible, or validated Phoc-supported configuration). Enumerate actual outputs and transform support, plus display pipeline quirks in `configs/s10plus/display/nuxel-s10plus-display.sh`. Do not use xrandr in Wayland mode or implement a mere whole-page CSS `rotate()`; don't claim generic DRM/KMS output support if S10+ presently relies on Samsung framebuffer/screencopy integration.

Rotate the display through compositor/window sizing APIs where available. Adjust touchscreen absolute coordinate transform/calibration (including 90°, 180°, 270°) and input seat mapping. Test top-left/touch-hitbox correspondence in all orientations. Ensure status bar, camera cutout/safe areas, Home desktop, four-icon shortcut dock, **persistent three-button system dock**, OSK above apps, active app frames, modal dialogs, Quick Settings overlay, notifications, browser viewport, recents, and keyboard focus are geometry-correct. Avoid clipped content, zooming Home, distorted pixel-art, and simultaneous scroll/swipe misclassification. Honor app requested rotation constraints where relevant and return meaningful unsupported states.

Lockscreen: preserve the existing artwork and draggable penguin lockhead, keep lockscreen layout in **known-safe portrait** by default unless its landscape implementation passes full touch-input/nonoverlap tests; do not let screen rotation or external outputs allow a lock bypass. Restore the user's selected unlocked mode after unlock. Power menu remains operable when locked. Maintain safe revert: if orientation change blanks display or input coordinates become unusable, revert automatically to last-good transform after a short bounded interval, without requiring touching a now-misaligned display.

## PHASE 4 — QUICK SETTINGS + FULL SETTINGS INTEGRATION

Transform the existing `qs-rotate` tile into a REAL, observable backend control. Design: tap shows current mode and/or quick switch; long-press opens a seven-choice menu; provide direct `Settings → Display & Orientation` with seven named radio choices, short descriptions, effective orientation, sensor availability, and clear errors. Preserve existing swipe-down shade behavior, navigation controls and theme. Reuse the supplied `assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png` if suitable; don't create random emojis/placeholder icons.

One source of truth shared by Quick Settings, Settings, `nuxelctl` if available, and compositor; update all screens immediately after mode changes and after reboot. Use authenticated local IPC and proper action authorization; reject malformed mode values. If sensors fail, keep manual modes enabled and auto modes disabled/marked unavailable. Support rollback if compositor can't apply requested transform. Add a controlled status/log endpoint for tests, not a mock toggle. Test a real portrait→landscape→reverse sequence without losing touchscreen accuracy.

## PHASE 5 — USB-C TO HDMI / EXTERNAL MONITOR: HARDWARE-FIRST

The Galaxy S10+ can output video to compatible HDMI hardware under Samsung's original stack, but that does **not** establish that Fedora/Nuxel's vendor Linux drivers support USB-C DisplayPort Alternate Mode. Prove each stage.

**First protect the USB recovery console.** The S10+ has a single USB-C port. External-display adapters may change USB roles/alt mode and disconnect the only live USB serial interface. Before plugging in HDMI, preserve an alternate independently verified diagnostic/recovery method (e.g. compatible powered hub with working USB data path or reliable wireless admin transport) or conduct a controlled owner-supervised test with timed recovery, pre-captured logs, and no write/boot-critical changes. Never assume a passive USB-C→HDMI cable works with any phone; establish DP Alt Mode vs DisplayLink USB graphics vs HDMI conversion technology, which are distinct.

Document the *exact* adapter/dock chipset and power arrangement. Read `/sys/class/typec/`, USB power/data roles, `lsusb`, USB PD/TCPC/typec drivers, relevant kernel config, `dmesg -w` while hotplugging, DP alt-mode negotiation, mux/PHY lane ownership, DRM connector discovery (`/sys/class/drm/*/status`, `modetest`/`drm_info` if available), EDID and output modes. Examine Samsung Exynos display/DPU/DP driver support in the present vendor tree and device tree; do not infer from support in Android. A missing `/sys/class/typec` doesn't itself prove hardware lacks DP; record whether vendor interfaces replace generic Type-C class.

**Stage gates:**
1. Correct USB-C adapter recognized and phone retains recoverability.
2. Alt-mode/DP negotiation conclusively established or documented as missing.
3. Display connector + EDID/modes recognized or explicit blocker.
4. Stable actual rendered Nuxel pixels visible on monitor.
5. Correct phone/external hotplug, disconnect, power, audio policy and touch behavior.

Choose `Mirror phone` as primary mode. Provide `External display / Extend` ONLY if compositor and display hardware really support independent outputs and input/cursor management. For real hardware support, implement safe modesetting, scaling/aspect ratio/letterbox, hotplug detection, explicit mode selection, output reset/recovery, display/lockscreen privacy, blank/display power off behavior, and user-facing Settings → Display → External Display status. Do not rotate the external monitor whenever phone rotates unless user chooses it. Never invent a second monitor in WebKit as a substitute for a real connector.

Do NOT install Samsung DeX/Android proprietary binaries as a workaround. Do NOT modify Type-C mux, PMIC, boot partitions or regulators experimentally. If drivers/firmware are missing, produce a researched separate hardware enablement plan identifying source path, kernel config, device-tree/driver/PHY gaps, required firmware, upstream references, risk, and exact non-boot-critical changes possible. Don't claim success without visible HDMI output verified by owner.

## PHASE 6 — WIRELESS CASTING: HONEST CAPABILITY-FIRST

Implement the best **actually supported** mirroring transport after capability tests, preferably with two independent progressive paths:

**Path A — Miracast / Wi-Fi Display**: Investigate `gnome-network-displays` as a reference (not an automatically compatible drop-in). Check `iw phy` P2P capabilities, NetworkManager-managed P2P device, `wpa_supplicant` P2P/WFD support, radio concurrency with current Wi-Fi, device discovery, P2P group association, RTSP session, working H.264 encoder (`openh264`, `x264`, verified GStreamer elements), PipeWire/portal/Phoc screen capture, and optional audio routing. GNOME Network Displays' upstream workflow targets Mutter screencast portal or X11 fallback; Nuxel's **Phoc** compositor needs a real verified screencast implementation and may need a custom adapter/backend. Do not present a Miracast button unless its capture/transport pipeline actually functions.

**Path B — LAN/WebRTC or authenticated local screen share**: If Miracast is blocked, implement a secure, user-started local-network casting option only when real screen capture exists. Use Wayland compositor screencopy/portal if supported, a robust frame pipeline, bounded software encoding, optional WebRTC/HTTPS playback via browser on an external device; explicitly require user consent, pair code/token, network scoping, authentication, session stop/revoke, no background broadcasting, sensible quality caps, frame pacing, resolution selection, and lockscreen privacy (pause/redact on lock, not capture lockscreen secrets). No unauthenticated public LAN HTTP frame endpoint. Distinguish Chromecast/Google Cast receiver protocol from generic browser screen-sharing: do not label a WebRTC share as native Chromecast casting.

Implement `Quick Settings → Cast` and `Settings → Connected devices → Cast`, with state machine `UNAVAILABLE → DISCOVERING → CONNECTING → CASTING → STOPPING / ERROR`; list named supported receiver devices, audio availability, transport, permission/status and error evidence. If only WebRTC is possible, label it accurately as `Share screen` and do not fake discovery of smart TVs. Prove actual moving picture on a real receiving screen, rate/frame latency, audio separately, screen-off/lock privacy, disconnect and retry, and Wi-Fi reconnection. Avoid continuous GPU/CPU load or drain when casting is off.

**No unverified claim that wireless casting will work on the Exynos vendor kernel.** Record genuine blockers and keep independent haptics/orientation deliverables moving.

## PHASE 7 — WORKING NATIVE KEYBOARD HAPTICS

Preserve the keyboard that CURRENTLY accepts real text through the Wayland session. It must remain the only active OSK; never resurrect the broken blue WebKit keyboard overlay. Identify current OSK process/provider and whether it exposes per-committed-key feedback hooks. Investigate current Nuxel keyboard settings, `nuxel-haptics-bridge`, actuator tool and policy; detect actual device APIs (LED-class, timed_output, FF, etc.) and amplitude capability through hardware probes. Do not claim intensity support without a writable real amplitude interface. **Do not write vibrator sysfs from browser JavaScript.** Use the existing gated, authorized bridge and one rate-limited event path.

Extend `Settings → Keyboard → Haptic feedback`:
- `Keyboard haptics`: ON **by default** for new profiles, subject to the existing global haptics master switch; migrate old preferences without involuntary re-enabling a disabled global switch.
- `Intensity`: Low (default, subtle), Medium, High **only when genuine actuator strength is adjustable**. Optionally an accessible slider mapped to tested hardware range; if hardware is on/off or duration-only, explicitly label `Pulse duration / feel` instead and avoid false claimed amplitude changes.
- Optional `Test haptic` button guarded by explicit user click and bounded duration; disable when actuator unavailable.
- Persistence in Nuxel's shared keyboard settings store with schema validation, atomic writes, immediate apply and reboot survival; synchronize Settings, haptic bridge and OSK. No independent duplicated configuration copy overriding changes on startup.

Start with a bounded 8–15 ms candidate pulse and conservative hardware-safe amplitude, only after an **accepted keypress** (not pointer motion, mere touch-down, or repeated focus events). Use asynchronous dispatch so vibration never blocks text input; throttle key repeat and avoid unbounded queue; default no feedback on sensitive accessibility/system gestures unless permitted; follow global Haptics OFF, privacy, battery and quiet-mode policies. Verify hardware cannot be overdriven by choosing "High"; map levels to verified safe limits. Check sound mode behavior according to explicit user preference; do not assume silent mode always disables typing haptics.

**Owner tests:** Type in Calendar, Settings, Wi-Fi password, Browser URL; verify exactly one light tactile pulse per normal key; no double vibration; compare Low/Medium/High if amplitude is real, verify OFF / global OFF, idle and lockscreen no unintended buzzing; hide/show keyboard, rotate display, and reboot. If no real haptic event hook is available in the OSK, inspect source or upstream extension and integrate correctly; do not use unrelated touchscreen-down events as a fake substitute.

## PHASE 8 — RESOURCE, PRIVACY, POWER, SECURITY

The phone has previously run warm even with display off; don't regress it. Suspend sensor sampling and casting when unused; prevent busy loops and persistent encoding after disconnect; avoid spawning processes for each sensor tick or key. Confirm idle power/CPU frequency and wakeups with mode fixed versus auto, monitor casting overhead, reduce background services accordingly. Do not override the one-minute lockscreen/timeout implementation. When the screen is locked, the user must not gain interaction with apps via external display, keyboard, mouse or a remote casting viewer; mask/redact sensitive notifications appropriately. Avoid exposing compositor or haptic privileged actions over an unauthenticated HTTP endpoint. Validate local requests, authorization and source of events.

## PHASE 9 — TESTING (AUTOMATED + REAL DEVICE)

Create targeted unit tests and integration tests covering:

- Sensor enumeration, accelerometer orientation and verified axis/mount matrix; missing/garbled/disconnected sensor; gyro optional.
- Seven mode policy set/restore, all four fixed transforms, restricted auto rules, edge/flat cases, hysteresis and restart.
- Wayland output transform and touch calibration (all four corners, keyboard interaction, gestures, status/dock geometry), safe revert on display failure.
- Quick Settings and Settings matching mode, persistent config across reboot; no cosmetic toggle success.
- Lockhead drag/unlock, Power menu and keyboard staying usable after rotation; existing app lifecycle/navigation functions.
- HDMI discovery, USB role/PD/alt-mode decision trace, adapter disconnect, EDID/modes, successful visible mirror if supported, USB console preservation.
- Cast discovery and real media path with transport-appropriate tests; capture permission/privacy on lock, broken Wi-Fi, cancellation, 15-minute resource stability.
- Single OSK, haptic ON default for new profile, OFF/global OFF overrides, genuine hardware intensity versus duration-only, no keypress double delivery, shutdown on lock, persisted settings after reboot.
- Thermal / idle regressions versus preflight baseline.

Tests must distinguish simulated output from real S10+ evidence. Include hard negative cases and regression tests for the navigation buttons, resource meters, battery, lockscreen and Wi-Fi.

## PHASE 10 — STAGED LIVE USB DEPLOYMENT

Milestone A: Sensor readings + manual orientation modes → offline tests → safe deploy → real touch check.  
Milestone B: Automatic 4-way and restricted modes + Quick Settings/Settings → verify and reboot after permission.  
Milestone C: Native keyboard haptics + intensity Settings → physical keypress/rotation/lock verification.  
Milestone D: Type-C/HDMI read-only capability tests; guarded external-output bring-up only if USB recovery is assured.  
Milestone E: Cast proof-of-concept through verified transport, then UI and hardening.

For each: prepare backups/checksum manifest; build ARM64 dependencies (cross-build correctly or native Fedora `aarch64`), deploy only needed userspace/config files, restart affected services, check actual loaded revisions, collect bounded logs, physically verify, rollback on failure, commit coherently. Don't blindly install a desktop environment or change the main graphical session just to use a feature. Do not reboot/flash to test HDMI when simple read-only capability discovery suffices; a kernel enablement project requires a separate approved mission.

## PHASE 11 — OWNER ACCEPTANCE

**Rotation:** From Home open QS mode picker. For each fixed orientation rotate and touch corners. Auto: turn through all four sides; Auto portrait: only upright/upside-down, never sideways; Auto landscape: only two sideways positions; flip upside-down and back; confirm screen not falsely rotating face-up; open Calendar, Wi-Fi Settings, Browser, OSK and custom lockscreen. Reboot, confirm saved mode.

**Haptics:** Type a sentence into Browser and Calendar, low default felt, toggle off/on, test available strengths, no duplicate taps or OSK regression, reboot retains preferences.

**HDMI:** Only after proven USB recovery: connect a known DP Alt Mode-capable HDMI adapter with an actual monitor, verify physical video (and optional audio separately), unplug and restore phone view.

**Casting:** Show actual moving Nuxel screen on a real receiver or accurately labeled authenticated browser screen share, stop, lock, wake, disconnect, reconnect. No secret lockscreen capture.

## FINAL REPORT FORMAT / DEFINITION OF DONE

| Feature | Source + tests | Deployed | Hardware/owner proof | Blocker |
|---|---|---|---|---|
| Accelerometer / gyro detection | | | | |
| 0/90/180/270 manual modes | | | | |
| Auto all orientations | | | | |
| Auto portrait | | | | |
| Auto landscape | | | | |
| QS / Settings / persistence | | | | |
| Touch mapping / keyboard after rotation | | | | |
| USB-C DP alt mode and HDMI physical output | | | | |
| Casting actual screen/video | | | | |
| Keyboard haptics / real intensity | | | | |
| Rotation/haptics survive reboot | | | | |
| Lockscreen, nav, USB console preserved | | | | |

Provide source/commit/PR IDs, real device/kernel interfaces found, sensor-axis/mount matrix, Wayland/compositor proof, haptics hardware capabilities, USB adapter/chipset and HDMI negotiation traces, capture/encoder/casting evidence, resource/thermal deltas, tests, deployment receipts, SHA-256, rollback, and exact reasons for BLOCKED/UNVERIFIED. Update device support docs and capability matrix based only on evidence; do NOT claim USB-C HDMI or Miracast success merely because corresponding hardware worked under Samsung Android.

**FINAL GOAL: A penguin that rotates on command, rotates correctly by gravity, outputs to a bigger screen wherever this kernel truly supports it, and gives subtle tactile confirmation on every real keyboard keypress — without breaking the phone. BUILD, TEST, DEPLOY, PROVE. 🐧🔥**
