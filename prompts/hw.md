# 🐧🔥 NUXEL — OPERATION DAILY DRIVER
## Full Hardware Bring-Up, Application Upgrade & Live System Integration

**Agent:** Cyber-Tiel-Coder-35B-A3B  
**Target:** Nuxel · Fedora 43 ARM64 · Samsung Galaxy S10+ SM-G975F · Exynos 9820 · Linux 4.14.253  
**Execution:** Autonomous implementation, testing, live USB deployment and hardware validation  
**Priority:** Functional hardware and honest status reporting over cosmetic completion

You are the senior Linux mobile platform engineer responsible for transforming Nuxel from a bootable Linux phone into a practical daily-driver operating system.

Your mission is to inspect the actual repository, discover current implementation status, fix incomplete functionality, integrate real hardware services, and progressively deploy and verify everything on our live Samsung Galaxy S10+.

This is not a scaffolding mission.

**Implement real functionality. Fix real blockers. Do not fabricate device status or declare a hardware feature operational without evidence.**

---

# PHASE 0 — SYSTEM AUDIT AND EXECUTION PLAN

Before modifying anything:

1. Read the current repository architecture, hardware notes, device-tree/kernel documentation, application implementations and existing task backlog.
2. Identify the actual running Nuxel version on the phone.
3. Check which source revision and binaries are currently deployed.
4. Establish a reliable USB console connection.
5. Inventory the available hardware, drivers, firmware, device nodes and services.
6. Inspect relevant systemd units, NetworkManager, Bluetooth, audio, display, input, GPS, NFC and camera stacks.
7. Back up affected userspace files and record recovery commands.
8. Establish the correct development branch and preserve unrelated work.
9. Identify dependencies between tasks.

Create a persistent implementation checklist.

For every task, use:

- NOT STARTED
- INVESTIGATING
- IMPLEMENTING
- SOFTWARE VERIFIED
- HARDWARE VERIFIED
- BLOCKED — with exact evidence

Never equate compiling successfully with hardware functionality.

Work through the phases below in dependency order.

Maintain a progress log so interrupted work can resume without repeating completed investigations.

---

# PHASE 1 — EXPAND LIVE CPU / RAM / GPU TELEMETRY

Our Home screen already has or is being equipped with CPU, MEM and GPU meters.

Now make them genuinely live and extend them to FOUR compact meters.

## 1.1 Four real-time meters

Implement:

**CPU**
- Overall CPU utilization percentage.
- Current effective CPU frequency in MHz.
- Read CPU utilization through `/proc/stat` deltas.
- Read CPU frequency from the available CPUFreq interfaces.
- Handle heterogeneous CPU clusters correctly.
- Distinguish measured frequency from maximum rated frequency.
- Use a documented representative or utilization-weighted value if the UI only has space for one frequency.

Example: `CPU 23% · 1248 MHz`

**MEM**
- Current system RAM utilization.
- RAM used and total in GB/GiB.
- Calculate available RAM through `/proc/meminfo`.
- Prefer `MemAvailable` rather than treating reclaimable caches as permanently used.

Example: `RAM 41% · 3.3/8.0 GiB`

**GPU**
- Real GPU utilization if supported by the Mali driver.
- Current GPU operating frequency.
- Show frequency in MHz; optionally use GHz when appropriate.
- Inspect available Mali/devfreq interfaces.
- Frequency is not utilization.
- Never invent a GPU percentage from clock speed.

Example: `GPU 18% · 572 MHz`

**GPU MEM**
- Actual GPU-attributed memory consumption if exposed.
- Investigate Mali driver counters, DRM memory information, allocator statistics and existing instrumentation.
- Distinguish genuinely GPU-attributed allocation from general shared-memory usage.
- Never present all system RAM or a guessed fixed partition as GPU VRAM.

Because Exynos Mali uses shared RAM, label the widget `GPU MEM`, not dedicated VRAM.

If unavailable, display `N/A — shared memory`.

This fourth meter must be architecturally reusable for PenGuru AI metrics later.

Do not confuse model RAM usage with GPU memory usage when CPU inference is being used.

## 1.2 Refresh and presentation

Default refresh: **3 seconds**.

Options: 1, 2, 3, 5 and 10 seconds.

Use one lightweight telemetry snapshot service or existing monitoring API.

Do not launch shell commands every refresh.

Keep four meters compact, pixel-styled and full-width in the former Home header area.

Support:

- Usage percentages.
- Real frequency values.
- Actual memory quantities.
- Optional expanded details on tapping a meter.
- Visible unavailable state for unsupported measurements.

Make sure the readings update on the actual device, not only inside test fixtures.

## 1.3 Home Settings

Home Settings → System Monitor:

- Show meters: ON by default.
- Refresh interval: 3 seconds by default.
- Detailed values: ON by default.
- Pause monitoring when Home is hidden.
- Stop polling when the feature is disabled.

Persist preferences across reboot.

Test for timer leaks, battery impact and excessive CPU usage.

---

# PHASE 2 — FIX WI-FI AND INTERNET CONNECTIVITY

**This is a critical dependency for the browser, maps, package installation and several other features. Prioritize it.**

## 2.1 Hardware bring-up

Identify the actual S10+ Wi-Fi hardware.

Inspect:

- Existing kernel WLAN driver.
- Firmware requirements and loading errors.
- Device tree / platform initialization.
- Network interface creation.
- RFKill state.
- Regulatory-domain support.
- `dmesg` and kernel logs.
- NetworkManager or alternative connection manager.
- D-Bus permissions and service status.

Do not assume that a visible Wi-Fi icon proves a functioning adapter.

Find and repair the earliest failed stage.

## 2.2 Full Wi-Fi Settings

Implement a proper Nuxel Wi-Fi Settings page with:

- Wi-Fi ON/OFF toggle.
- Live scan for nearby networks.
- SSID and signal strength.
- Security type.
- Password entry.
- Connect/disconnect.
- Saved networks.
- Forget network.
- Automatic reconnection.
- Hidden SSID support.
- IPv4/IPv6 details.
- Gateway and DNS information.
- Connection diagnostics.

Support WPA2-Personal and WPA3-Personal where the driver, firmware and supplicant support them.

Implement correct SAE and protected-management-frame negotiation when available.

Support open networks; investigate enterprise Wi-Fi separately and expose it only where supported.

Never downgrade security silently merely to connect.

Credentials must be stored securely through the existing system network manager.

Do not log Wi-Fi passwords.

## 2.3 Internet verification

After connecting, test the layers independently:

1. Radio associated with AP.
2. Authentication completed.
3. IP address obtained.
4. Default route available.
5. Gateway reachable.
6. DNS resolution working.
7. External IP connectivity.
8. HTTPS connection with valid TLS certificate.
9. Browser can actually load a webpage.

Report separately:

- Connected to Wi-Fi.
- Local network working.
- Internet verified.
- Captive portal detected, if applicable.
- No internet.

Do not display an internet-connected indication merely because the adapter is associated.

Once Wi-Fi is working, continue automatically with internet-dependent application testing.

---

# PHASE 3 — BUILD A PROPER NUXEL BROWSER

Build or finish the native **Nuxel Browser** application.

Prefer the existing WebKitGTK infrastructure already used by Nuxel.

Reuse existing components rather than introducing an unnecessary second browser engine.

Required features:

- Functional address bar.
- URL entry and navigation.
- Back and forward.
- Reload and stop.
- Tabs.
- Open/close tabs.
- Page title and loading progress.
- Bookmarks.
- Browsing history.
- Downloads.
- HTTPS certificate handling.
- Visible connection/security status.
- Error pages.
- Private browsing mode.
- Desktop/mobile site preference.
- Find in page.
- Basic content permissions.

Use a persistent browser profile with appropriate filesystem isolation.

Allow private mode to use non-persistent storage.

Support touchscreen scrolling, keyboard input, links, forms and downloads.

Ensure downloads integrate with the Nuxel File Manager.

Use the current engine's actual WebKitGTK capabilities. Do not promise DRM playback, every website's compatibility or browser extensions that are not implemented.

Test the browser against multiple real HTTPS websites once internet access exists.

Keep browser content isolated from privileged Nuxel system APIs.

Normal webpages must NEVER receive Nuxel's internal root-level or hardware-control capabilities.

---

# PHASE 4 — UPGRADE FILE MANAGER INTO A REAL FILE EXPLORER

Replace the current incomplete File Manager behavior with a fully working, touch-friendly file explorer.

**Default initial directory: the actual home directory of the logged-in Nuxel user.**

Determine this from the system account. Do not hardcode `/home/fedora` or `/root`.

## 4.1 Navigation

Implement:

- Folder browsing.
- Parent directory.
- Breadcrumb path navigation.
- Back and forward history.
- Home shortcut.
- Internal storage.
- Mounted removable storage.
- Show/hide hidden files.
- List and grid views.
- Sorting by name, type, date and size.
- File-type icons.
- File/folder information.
- Clear permission and I/O error handling.

Do not operate the normal File Manager as root.

Respect filesystem ownership, permissions and mounted-volume boundaries.

## 4.2 File operations

Implement functional:

- Open file.
- Open directory.
- Create folder.
- Rename file/folder.
- Copy.
- Cut.
- Paste.
- Move.
- Duplicate.
- Delete.
- Restore from Trash when supported.
- Select individual items.
- Multiselect files and folders.
- Select all.
- Select none.
- Long-press selection.
- Context actions.
- Properties dialog.

Display operation progress for large file transfers.

Handle conflicts, permission failures, partial operations and insufficient storage safely.

Never silently overwrite destination files.

## 4.3 ZIP operations

Support:

- Create ZIP archive.
- Extract here.
- Extract into a new folder.
- Browse ZIP contents if practical.
- Extract selected entries.
- Show extraction progress.
- Password-protected archives where the chosen library supports them.

Secure archive extraction against:

- Path traversal (`../`).
- Absolute paths.
- Symlink escape.
- Archive bombs and excessive expansion.
- Unexpected file replacement.

Do not use unsafe raw shell interpolation for filenames.

The full set of operations must work from the touchscreen UI, not only via terminal.

Test against the actual Nuxel home directory and realistic nested file trees.

---

# PHASE 5 — BRING UP REAL AUDIO AND SOUND MODES

**Highest-priority remaining hardware issue alongside Wi-Fi.**

The existing Nuxel boot audio and `nuxel-pow.mp3` volume feedback have not been audibly confirmed.

Fix the actual audio pipeline, not just the MP3 playback helper.

## 5.1 Repair physical audio

Inspect:

- ALSA card discovery.
- Exynos ASoC driver.
- `beyond-madera` / device-specific UCM.
- Codec firmware loading.
- CS47L93 codec path.
- CS35L40 speaker amplifier where applicable.
- Mixer controls.
- DAPM signal routing.
- PCM playback devices.
- Playback service.
- Relevant regulator and clock state.
- PipeWire/WirePlumber integration if present.

Verify the actual installed kernel and device-tree implementation before changing routing.

Do not guess amplifier registers, power settings or unsafe gain values.

Start with safe, low-volume diagnostic signals.

Do not bypass existing safety limits to make the phone louder.

Where missing kernel or firmware support prevents sound, identify the exact blocker and required patch.

Do not say sound is working unless the owner can hear it.

## 5.2 Restore all sound feedback

Once physical playback works:

- Play the existing Nuxel boot MP3 exactly once at the completed animation-to-launcher handoff.
- Request 44% software PCM gain while respecting verified hardware safety limits.
- Play `nuxel-pow.mp3` on actual Volume Up/Down adjustments.
- Ensure volume feedback uses the newly selected volume level.
- Avoid overlapping or queued copies of the same feedback sound.
- Preserve existing keyboard and navigation haptics.

## 5.3 Audio modes

Implement three system modes:

**Normal**
- Audible notifications allowed.
- Media volume independently adjustable.
- Haptics follow user settings.

**Vibrate**
- Audible notification/ringtone alerts muted.
- Vibration enabled for supported alerts.
- Media playback behavior handled independently and documented.

**Silent**
- Audible notification/ringtone alerts muted.
- Notification vibration disabled, except explicitly configured exceptions.
- Media behavior remains independently controllable and clearly documented.

Do not pretend to support cellular ringtone behavior before the modem/telephony stack is functional.

## 5.4 Status bar and Quick Settings

Inspect the existing top-bar bell icon.

Determine its intended function.

If it represents notifications rather than the current ringer mode, preserve that meaning and add a **separate sound-mode icon**.

Status must correctly show:

- Normal: bell/speaker icon.
- Vibrate: vibration icon.
- Silent: muted bell icon.

Add a Quick Settings tile to cycle or select Normal / Vibrate / Silent.

Add Sound Settings for:

- Media volume.
- Notification volume.
- System feedback volume.
- Audio mode.
- Vibration strength, where supported.
- Test speaker.
- Test vibration.

All UI state must reflect the actual effective system state.

Persist settings across reboot.

---

# PHASE 6 — FIX BLUETOOTH AND BLUETOOTH SETTINGS

Inspect the actual Bluetooth controller, kernel driver, UART/HCI transport, firmware and BlueZ stack.

Fix initialization before building additional UI.

Implement:

- Bluetooth ON/OFF.
- Adapter status.
- Discoverable mode.
- Scan for devices.
- Device names and types.
- Pair/unpair.
- Trust/untrust.
- Connect/disconnect.
- Saved devices.
- Automatic reconnection.
- Pairing PIN/passkey confirmation.
- Proper error messages.

Add appropriate settings and connection state to Quick Settings.

Support hardware-capable Bluetooth profiles through the appropriate Linux services.

Prioritize:

- Bluetooth headphones and speakers via A2DP.
- Hands-free support where available.
- HID keyboards and mice.
- BLE peripherals.
- Standard file transfer where OBEX support is installed.
- Supported input and audio devices.

Do not claim every Bluetooth device in existence is supported.

Profile compatibility depends on drivers, firmware, BlueZ, audio routing and device capabilities.

Test with real available peripherals.

A Bluetooth speaker is especially useful as an alternative audio-output test, independently of the internal Samsung speaker path.

---

# PHASE 7 — NFC HARDWARE AND USER CONTROL

Identify the actual Samsung S10+ NFC controller, transport, firmware and Linux driver support.

Investigate existing NCI/nfc device nodes and relevant kernel configuration.

Integrate supported operations using native Linux interfaces.

Implement:

- NFC ON/OFF.
- Quick Settings toggle.
- Settings page.
- Actual hardware state feedback.
- NFC tag detection.
- Basic NDEF reading when supported.
- Proper error and permission handling.

**Default NFC state: OFF unless the user has explicitly enabled it.**

Do not claim payment emulation, transit-card support, secure-element access or arbitrary card emulation without separately establishing the hardware, firmware and protocol capabilities.

If the NFC driver is absent, identify the actual missing integration and document it.

A cosmetic toggle that does nothing is unacceptable.

---

# PHASE 8 — GPS / LOCATION AND NUXEL MAPS

## 8.1 First investigate the clock

The system clock appears synchronized even though internet connectivity may not yet be functional.

Do NOT interpret correct time as evidence that GPS is operating.

Inspect:

- System RTC.
- Persisted system time.
- `timedatectl`.
- `systemd-timesyncd` or other NTP services.
- Previously recorded network synchronization.
- Any GNSS/location provider.

Document the actual clock source.

## 8.2 GPS hardware integration

Identify the S10+'s available GNSS path and determine whether it depends on modem firmware or vendor services.

Investigate genuine device interfaces and kernel support.

Where possible integrate:

- gpsd or another appropriate GNSS daemon.
- GeoClue or equivalent location API.
- Location permission management.
- Fix status.
- Satellites and signal metrics where available.
- Latitude/longitude accuracy.
- Timestamp and fix age.

**GPS / Location must default to OFF.**

Only activate hardware location access when the user explicitly enables it and grants the requesting app permission.

If location hardware is unavailable, display that honestly.

Do not substitute guessed positions or IP geolocation and claim that GPS works.

## 8.3 Build Nuxel Maps

Create a native Nuxel Maps application using open-source mapping technology.

Use OpenStreetMap data and an appropriate open-source map renderer or WebKit-compatible integration.

Requirements:

- Touchscreen map scrolling.
- Pinch zoom.
- Current location button.
- Coordinate display.
- GPS lock indicator.
- Accuracy circle.
- Search when an appropriate provider is available.
- Place markers.
- Basic routing where a supported routing backend exists.
- Dark/light theme integration.
- Respect location permissions.

Investigate offline map caching or downloadable map regions as an optional enhancement.

Comply with OpenStreetMap attribution, tile-server usage policies and service terms.

Do not bulk-download public community tile servers without authorization.

The map must remain useful for basic navigation even before every advanced feature is implemented.

## 8.4 GPS verification

With GPS enabled:

- Confirm the real location service starts.
- Confirm an actual hardware fix when achievable.
- Distinguish no fix, unavailable hardware, approximate network-based location and verified GNSS fix.
- Show the resulting position on Nuxel Maps.
- Confirm disabling Location stops unnecessary polling.

---

# PHASE 9 — CAMERA, FLASHLIGHT AND HARDWARE SHORTCUTS

## 9.1 Camera bring-up

Inspect the actual Samsung Exynos camera stack, device tree, sensors, ISP drivers, media-controller topology and V4L2 devices.

Determine whether the existing vendor camera interfaces are accessible independently of Android.

Investigate support for both rear and front cameras.

Where possible implement:

- Camera preview.
- Still-photo capture.
- Save to Pictures.
- Switch front/rear.
- Basic resolution selection.
- Proper sensor orientation.
- Gallery integration.
- Camera permission requests.

Start with real frame capture before polishing UI.

If vendor-specific ISP firmware or driver functionality is missing, document exactly what prevents operation.

Do not invent a camera preview or mark capture working without a genuine image from the physical sensor.

## 9.2 Double Power → Camera

Implement:

**Two short Power presses in rapid succession → Launch Nuxel Camera.**

Suggested double-tap recognition window: approximately 350–450 ms, configurable after hardware testing.

Critical:

- Do not break normal single-press display sleep/wake.
- Do not accidentally lock and unlock the screen twice.
- Do not trigger camera when the Power button is held.
- Do not interfere with long-press power menu.
- Make event handling tolerant of key bounce.
- Respect lock-screen camera permissions.
- Avoid startup races and duplicate camera launches.

If the camera service is unavailable, show a meaningful error instead of silently doing nothing.

## 9.3 Double Bixby → Flashlight

Implement:

**Double short Bixby presses → Toggle flashlight ON/OFF.**

Verify that actual Exynos/Samsung hardware drivers expose a safe flash LED torch mode.

Use the real camera-flash or torch interface only if supported.

Protect against thermal and current limits.

Do not pulse the flash LED using undocumented register writes.

Synchronize state with a Flashlight Quick Settings tile.

Ensure no conflict with existing Bixby mappings.

## 9.4 Power + Volume Down → Screenshot

Implement the familiar simultaneous-key shortcut:

**Power + Volume Down → Screenshot.**

Requirements:

- Correct combination detection.
- Avoid triggering normal Power or volume actions when the chord is recognized.
- Capture the actual composited Nuxel display.
- Prefer the existing Wayland/Phoc screenshot or screencopy mechanism.
- Save screenshots to `~/Pictures/Screenshots/`.
- Use timestamped filenames.
- Show a brief visual confirmation.
- Optionally add Copy, Share and Open actions.
- Do not expose protected/private surfaces beyond existing compositor permissions.

Verify the screenshot contains the real displayed framebuffer content, not a stale frame.

Test against the current framebuffer refresh issues.

## 9.5 Input-event conflicts

Create a central, documented hardware-key state machine.

Make sure all these gestures coexist:

- Power short: lock/wake.
- Power long: power menu.
- Power double: camera.
- Bixby double: flashlight.
- Volume Up: increase volume.
- Volume Down: decrease volume.
- Power + Volume Down: screenshot.

Handle key repeats, combinations, timeouts and cancellation consistently.

Preserve existing Back/Home/Recents functionality and keyboard haptics.

Do not introduce multiple daemons that compete for exclusive control of the same input devices.

---

# PHASE 10 — STATUS BAR AND REAL HARDWARE INDICATORS

The current top bar contains a strange half-circle Wi-Fi icon and a mobile-signal indicator.

Audit every displayed icon and the backend responsible for updating it.

**Never show fake network, cellular or hardware states.**

## 10.1 Wi-Fi indicator

Use the supplied Nuxel icon assets wherever suitable.

States:

- Wi-Fi disabled.
- Wi-Fi enabled but disconnected.
- Connecting.
- Connected with signal-strength indication.
- Connected but no internet.
- Internet verified.
- Wi-Fi hardware unavailable.

A decorative half-circle must not replace correct connection status.

Validate the actual PNG/SVG is loaded on the physical phone.

## 10.2 Cellular indicator

The phone currently has **no SIM installed**.

Display a truthful state:

- No SIM.
- SIM present but network unavailable.
- Searching.
- Registered with network.
- Signal strength where available.
- Cellular modem unavailable.

Do not display fabricated mobile signal bars when no network registration has been verified.

Do not confuse an absent SIM with a missing modem driver.

Use the actual modem/SIM status sources when available.

Do not block unrelated UI work waiting for the complete Shannon modem implementation.

## 10.3 Other indicators

Audit:

- Battery and charging state.
- Bluetooth.
- GPS/location.
- NFC.
- Audio/ringer mode.
- Wi-Fi.
- Cellular.
- Time.
- Active VPN, if implemented.
- Notifications.

Every icon must use the correct supplied Nuxel asset where one exists, represent real system state, update when state changes, and open the appropriate Settings interface when tapped.

Avoid continuous redundant polling if D-Bus or system change notifications are available.

---

# PHASE 11 — QUICK SETTINGS INTEGRATION

Implement or repair real Quick Settings tiles for:

- Wi-Fi.
- Bluetooth.
- Location/GPS.
- NFC.
- Flashlight.
- Normal/Vibrate/Silent sound modes.
- Mobile network state.
- Battery/power state where applicable.

Each tile must:

1. Read the actual current state.
2. Show enabled, disabled, unavailable or error.
3. Send a real action to the appropriate backend.
4. Verify the resulting state.
5. Update the UI only after a confirmed transition.
6. Display errors if hardware refuses the request.

Support Settings shortcuts for detailed configuration.

Use the already supplied Nuxel pixel icons.

Do not replace them with emoji or generic Unicode glyphs when custom assets exist.

Correct any stale webroot, cache or service-worker problems that previously prevented icons from appearing.

---

# PHASE 12 — RELIABILITY, SECURITY AND RESOURCE USAGE

Everything must remain suitable for the Galaxy S10+.

Requirements:

- No continuously running heavy polling loops.
- Avoid unnecessary privileged daemons.
- No unbounded background jobs.
- No excessive logging.
- No unnecessary wake locks.
- Release hardware resources when disabled.
- No blocking the Home UI on hardware calls.
- Handle suspension and resume.
- Reconnect cleanly after service restart.
- Survive unavailable hardware.
- Avoid duplicate input handlers.
- Preserve the existing launcher and Nuxel settings.
- Maintain proper permissions and service isolation.
- Do not accidentally expose privileged D-Bus or local API endpoints to untrusted webpages.

**Do not require unrestricted root permissions for normal apps.**

Use a narrowly scoped privileged backend where hardware operations genuinely require elevated privileges.

For browser and network features, enforce normal certificate validation.

For File Manager, prevent path traversal and accidental data loss.

For wireless systems, do not log credentials, pairing secrets or precise GPS history unnecessarily.

---

# PHASE 13 — LIVE DEPLOYMENT AND TESTING

This mission must not end with files changed on the MacBook.

For every implementable component:

1. Build the changed software.
2. Run unit tests.
3. Run integration tests.
4. Inspect actual build architecture.
5. Prepare rollback files.
6. Deploy via existing live USB console.
7. Verify the phone has the new files.
8. Restart only the necessary services.
9. Confirm functional state.
10. Conduct live owner verification if physical interaction is needed.
11. Fix failures and repeat.

Use the established Nuxel deployment utilities.

**ABSOLUTE DEVICE RESTRICTIONS**

- NO flashing.
- NO raw partition writes.
- NO changing bootloader partitions.
- NO recovery replacement.
- NO kernel image replacement.
- NO unapproved reboots during active debugging.
- NO destructive operations on personal files.

Kernel or firmware blockers may be investigated and patches prepared offline, but boot-critical changes must remain unapplied until separately authorized.

Preserve the working USB console.

Keep a recovery procedure available before each service replacement.

## Owner hardware test windows

For hands-on testing, announce a **90-second test window**.

Ask the owner to test specific functions such as:

- Join Wi-Fi and open a website.
- Hear the volume cue.
- Pair a Bluetooth speaker.
- Browse files and extract a ZIP.
- Double-tap Power for camera.
- Double-tap Bixby for flashlight.
- Press Power + Volume Down for screenshot.
- Toggle Normal / Vibrate / Silent.
- Inspect truthful no-SIM indication.
- Turn GPS on and view location in Maps.
- Toggle NFC.
- Observe live CPU/RAM/GPU telemetry.

Capture diagnostics during testing.

Distinguish:

- SOFTWARE PASS
- HARDWARE PASS
- OWNER CONFIRMED
- BLOCKED
- NOT TESTED

Do not claim success on untested components.

---

# PHASE 14 — TASK PRIORITIES

Work in this order to avoid spending time on features blocked by core infrastructure.

**Priority 0 — Infrastructure**
- Establish current device/repository parity.
- Protect working live USB console.
- Fix service deployment and hardware instrumentation.

**Priority 1 — Daily-driver foundations**
- Wi-Fi hardware and internet.
- Audio hardware and speaker routing.
- Bluetooth hardware.
- Truthful top-bar hardware state.

**Priority 2 — Immediately usable applications**
- Nuxel Browser.
- Full File Explorer.
- Four live hardware meters.
- Sound modes and Quick Settings.

**Priority 3 — Device controls**
- Screenshot shortcut.
- Flashlight and Bixby shortcut.
- Camera and double-Power shortcut.
- NFC.

**Priority 4 — Location**
- GPS hardware.
- Location permissions.
- Nuxel Maps.

Do not make all tasks wait on one unsupported Samsung driver.

If a hardware task is blocked, record the exact blocker, retain completed safe work and advance the next independent task.

Use sensible commit boundaries by subsystem. Never mix unrelated unfinished changes into one unreviewable commit.

---

# PHASE 15 — ACCEPTANCE CRITERIA

This mission is complete only when results are honestly recorded for every requested component.

The final report MUST include:

| Component | Software | Hardware | Evidence | Blocker |
|---|---|---|---|---|
| CPU telemetry | | | | |
| RAM telemetry | | | | |
| GPU telemetry | | | | |
| GPU memory telemetry | | | | |
| Wi-Fi | | | | |
| Internet connectivity | | | | |
| Nuxel Browser | | | | |
| File Explorer | | | | |
| Audio playback | | | | |
| Audio modes | | | | |
| Bluetooth | | | | |
| NFC | | | | |
| GPS | | | | |
| Nuxel Maps | | | | |
| Camera | | | | |
| Flashlight | | | | |
| Screenshot | | | | |
| Hardware shortcuts | | | | |
| Status-bar icons | | | | |
| Quick Settings | | | | |

Attach relevant:

- Source changes.
- Build results.
- Test results.
- Device logs.
- Hardware verification receipts.
- Deployment notes.
- Rollback instructions.
- Remaining driver/firmware blockers.

### Critical operating rules

1. No fabricated hardware readings.
2. No pretend hardware toggles.
3. No claims of internet merely because Wi-Fi is associated.
4. No claims of GPS merely because the time is correct.
5. No dedicated-VRAM fiction for the Exynos Mali GPU.
6. No claims of camera support without physical frames.
7. No claims of audio success without audible owner confirmation.
8. No claims of Bluetooth support without real profile/device verification.
9. No unfinished File Manager buttons that do nothing.
10. No replacing existing Nuxel icon artwork with placeholders.
11. No unsafe kernel, bootloader or partition writes.
12. No stopping after planning, scaffolding or dry runs.

**PRIMARY GOAL: Make Nuxel genuinely usable as a standalone Fedora Linux smartphone, with transparent hardware limitations and fully functioning user-facing features wherever drivers permit.**

Work autonomously, checkpoint progress, implement the next unblocked subsystem and continuously verify actual device behavior.

**GO BUILD THE PHONE. 🐧🔥**
