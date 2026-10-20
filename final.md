# 🐧🔥 NUXEL — OPERATION DAILY DRIVER v2
## Complete Hardware Bring-Up, Application Engineering, Dock & UI Repair, and Live S10+ Verification

**Agent:** Cyber-Tiel-Coder-35B-A3B  
**Project:** Nuxel — Linux on the Google Pixel  
**Current device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**Platform:** Samsung Exynos 9820 · Fedora 43 ARM64 · Samsung Linux 4.14.253  
**Environment:** Nuxel Home · WebKitGTK · Phoc/Wayland · Samsung framebuffer/display integration  
**Execution:** Autonomous implementation, testing, live USB deployment, hardware verification and checkpointing

---

# MISSION

You are the lead Linux mobile OS engineer responsible for advancing Nuxel from a bootable custom Linux operating system toward a genuinely usable daily-driver smartphone.

Inspect the actual repository and live device. Identify incomplete functionality, repair existing features, implement missing backend services, integrate hardware drivers and APIs, and verify the result on our running Galaxy S10+.

This is NOT a documentation-only, mockup-only or scaffolding mission.

**Implement functionality, deploy real changes, test them, repair failures and report evidence.**

The requested features include:

1. Four live CPU/RAM/GPU/GPU-memory meters with frequency and memory quantities.
2. Full Wi-Fi hardware bring-up and modern wireless connection management.
3. Internet connectivity verification.
4. A functional Nuxel Browser.
5. A complete graphical File Explorer.
6. Physical audio playback and sound-mode controls.
7. Bluetooth hardware, pairing and connected-device management.
8. NFC support and truthful on/off toggles.
9. GPS/location support and an OpenStreetMap-based Nuxel Maps application.
10. Camera hardware and application bring-up.
11. Power/Bixby hardware shortcuts and screenshots.
12. Accurate status-bar network, SIM, sound and hardware indicators.
13. Functional Quick Settings integration.
14. **Complete repair of the custom dock and panel backgrounds that are still not rendering.**
15. Correct loading and rendering of all supplied Nuxel pixel-art icons and graphics.

Preserve all functioning Nuxel services, UI behaviors and device interfaces.

---

now the dock background doesnt work anymore, and cant select another either now just displaying no background on dock.
and fix audio! and I noticed you added a wifi manager but I doint see any wifi settings in the settings app add the necessary maanger/settings in there please or add it as application if that is more reasonable/common/easy to do it and manage the stuff.

# PHASE 0 — PREFLIGHT, LIVE DEVICE AUDIT AND SAFE EXECUTION

Before modifying code:

1. Inspect the current repository, Git branch and worktree.
2. Read the Nuxel architecture, hardware bring-up notes, service definitions, UI documentation and deployment instructions.
3. Identify the current live S10+ userspace revision.
4. Verify which files and binaries are actually deployed.
5. Establish the existing MacBook-to-S10+ USB console connection.
6. Inspect the live service topology.
7. Inventory hardware drivers, firmware, device nodes, kernel configuration and relevant systemd services.
8. Back up all affected deployed files.
9. Record rollback commands.
10. Inspect existing application, Quick Settings, dock, asset and stylesheet implementations.
11. Identify dependencies and conflicts among these tasks.
12. Establish a persistent, resumable implementation checklist.

Use these statuses:

- NOT STARTED
- INVESTIGATING
- IMPLEMENTING
- SOFTWARE VERIFIED
- HARDWARE VERIFIED
- OWNER CONFIRMED
- BLOCKED — with exact evidence

Don't count compilation or a successful service restart as hardware verification.

Don't repeat work that is already genuinely functioning.

Maintain checkpoints between subsystems so the mission survives interruption or context exhaustion.

## Absolute device rules

- NO flashing.
- NO raw partition writes.
- NO bootloader modification.
- NO recovery replacement.
- NO kernel image replacement.
- NO destructive changes to personal files.
- NO unapproved reboots during active debugging.
- NO losing the USB console without a verified way to restore it.

Kernel, driver and firmware fixes may be researched and prepared offline. Boot-critical changes require separate authorization.

---

# PHASE 1 — REPAIR ALL NUXEL DOCK AND PANEL BACKGROUNDS

**HIGH PRIORITY — THE CUSTOM DOCK BACKGROUNDS ARE STILL NOT WORKING ON THE PHONE.**

The existing Nuxel interface contains custom pixel-art and futuristic graphics intended to replace boring default blue rectangles and generic panels.

These assets were previously supplied and may already exist in the repository.

However, their presence in source files does NOT prove that they're installed, loaded, rendered or visible in the running WebKitGTK interface.

## 1.1 Identify every dock and affected component

Inspect at least:

- Bottom Back/Home/Recents navigation dock.
- Application shortcut dock.
- Home application grid backgrounds.
- Quick Settings panel.
- Quick Settings toggle containers.
- Notification shade.
- App drawer background.
- Home screen panels.
- Other components that share the broken dock/panel styling.

Determine which components are intentionally supposed to use custom dock backgrounds and which should remain transparent.

Do not arbitrarily apply the same texture to every screen.

Preserve the visual distinction between navigation dock, app dock, background panels and overlay surfaces.

## 1.2 Locate original artwork

Search the repository for supplied assets, including:

- Dock background PNGs.
- Navigation bar background artwork.
- Pixel-style panel images.
- Quick Settings artwork.
- Transparent backgrounds.
- Existing Nuxel spritesheets.
- All custom app and toggle icon packs.

Use the EXACT owner-supplied artwork wherever it exists.

Do not generate replacement images, use emoji, insert generic Unicode symbols or substitute CSS gradients without a reason.

If required artwork is truly missing, document the missing filename and implement a temporary clearly labeled fallback without claiming the custom asset is installed.

## 1.3 Determine the actual reason the backgrounds fail

Trace the complete rendering path:

**Repository asset → build artifact → live filesystem → web server → WebKitGTK resource URL → CSS background → DOM element → final framebuffer.**

Inspect:

- Incorrect relative or absolute asset paths.
- `/assets/` webroot mapping.
- Missing files in deployment manifests.
- Mismatched filenames and casing.
- Incorrect MIME types.
- Missing PNG alpha channels.
- Cached old CSS or JavaScript.
- Stale service workers.
- Incorrect image dimensions.
- CSS selector specificity.
- Background images overridden by blue background colors.
- Stacking contexts.
- `z-index`.
- `overflow: hidden`.
- Transparent parent containers.
- Element height or width collapsing to zero.
- Incorrect `background-size`.
- `background-position`.
- `background-repeat`.
- CSS opacity and blending.
- High-DPI display scaling.
- Viewport/safe-area issues.
- WebKitGTK-specific CSS behavior.
- Graphics compositing and framebuffer refresh problems.

Specifically identify whether the old boring blue rectangle remains because:

1. The custom image doesn't load.
2. The CSS doesn't reference the image.
3. Another style overrides it.
4. The image is positioned offscreen.
5. The wrong component is being styled.
6. WebKit is serving old cached assets.
7. The correct image is loaded but not reaching the current displayed framebuffer.

Do not stop at the first plausible explanation. Verify the actual failure mechanism.

## 1.4 Bottom navigation dock

The three-button navigation area contains:

- Back.
- Home.
- Recents / App Switcher.

Preserve their existing behavior, including long-press functionality.

Replace the boring blue background with the appropriate custom Nuxel dock artwork.

Requirements:

- Dock spans the intended available bottom width.
- Artwork correctly reaches the bottom screen edge.
- Proper transparency around the decorative shape.
- No opaque rectangular image backdrop.
- Icons remain centered and correctly sized.
- Touch targets remain usable.
- Visual background does not intercept pointer events.
- No gaps during screen rotation.
- No stretching that destroys pixel-art edges.
- Correct layering of icons above dock artwork.
- Proper appearance on the live S10+.

Prefer a dedicated background/pseudo-element that doesn't alter the hitboxes.

Use pixel-preserving image scaling where suitable.

## 1.5 Application dock and Home panels

Fix the dock or panel behind the app shortcuts.

Requirements:

- Actual custom artwork visible.
- Correct width and alignment.
- Existing icon positions preserved.
- No blue fallback rectangle covering the image.
- Proper transparent edges.
- No clipping of app labels.
- No conflict with desktop swipe gestures.
- No overlap with the live system-monitor widget.
- Correct layout when switching between Home desktops.

## 1.6 Quick Settings and notification panels

Inspect whether custom graphics are intended behind:

- Quick Settings toggles.
- Quick Settings header.
- Expanded settings shade.
- Notification shade.

Apply the correct artwork without preventing scrolling, touch selection, notifications or toggles.

Avoid decorative images covering real interactive elements.

## 1.7 Ensure correct assets are actually deployed

Update all relevant:

- Asset packaging scripts.
- S10+ rootfs build manifests.
- Live deployment manifests.
- Static server configuration.
- Frontend resource paths.
- Service-worker/cache revisions.
- CSS/JS cache invalidation.

Verify the bytes of deployed PNG files against repository SHA-256 hashes.

Check actual resource HTTP responses, not just filesystem existence.

Inspect the loaded DOM and computed styles where possible.

Make the correct result visible immediately following deployment, without requiring the user to press Power twice or force arbitrary refreshes.

If the compositor/display pipeline is blocking presentation, diagnose and repair that separately rather than incorrectly marking the CSS task complete.

## 1.8 Dock verification

Acceptance requires:

- Physical display shows the custom bottom navigation background.
- Back/Home/Recents icons appear correctly above it.
- Application dock background is visible.
- Quick Settings background appears wherever designed.
- Transparency looks correct.
- No stale blue rectangles remain in components intended to use PNG artwork.
- All touch targets work.
- Existing swipe gestures still function.
- No display-refresh regressions.
- User confirms actual appearance.

If possible, capture a real framebuffer screenshot and compare it with the intended asset/layout.

**Do not claim success solely because CSS contains `background-image`.**

---

# PHASE 2 — FOUR LIVE HARDWARE METERS

Replace or upgrade the existing Home hardware-monitor widget.

Display four compact sections:

**CPU | RAM | GPU | GPU MEM**

All must update live.

## 2.1 CPU

Show:

- Current overall CPU utilization percentage.
- Current effective CPU frequency in MHz.

Compute utilization using deltas from `/proc/stat`.

Read frequency from verified CPUFreq interfaces.

Account for Exynos heterogeneous CPU clusters.

Use a documented representative frequency if only one can be displayed.

Do not confuse maximum rated frequency with current frequency.

Example:

`CPU 24% · 1248 MHz`

## 2.2 RAM

Show:

- Overall memory utilization.
- RAM used/total in GiB.

Use `MemTotal` and `MemAvailable` from `/proc/meminfo`.

Calculate used RAM consistently.

Example:

`RAM 46% · 3.7/8.0 GiB`

## 2.3 GPU

Show:

- Actual Mali GPU utilization percentage if available.
- Current GPU frequency in MHz/GHz.

Investigate:

- Mali-specific interfaces.
- `/sys/class/devfreq/`
- Platform driver instrumentation.
- GPU busy/idle counters.
- Existing GPU telemetry APIs.

Clock frequency is NOT utilization.

If a genuine utilization source doesn't exist, show GPU utilization as `N/A` but retain real GPU frequency if available.

## 2.4 GPU MEM

The S10+ Mali GPU uses shared system memory, not dedicated desktop-style VRAM.

Show GPU-attributed memory allocation only if accurately exposed by the running driver.

Potential interfaces include documented Mali memory-accounting data and supported DRM/allocator statistics.

Do not display total RAM as dedicated GPU VRAM.

If unavailable:

`GPU MEM · N/A`

This section should be reusable later for PenGuru local-AI memory monitoring.

## 2.5 Refresh policy

Default: **3 seconds**.

Options: 1, 2, 3, 5, 10 seconds.

Use one lightweight shared metrics collection mechanism.

Never spawn several monitoring subprocesses every second.

Requirements:

- Update visible values without rebuilding the entire widget.
- Pause sampling when Home is hidden.
- Stop unnecessary sampling when disabled.
- Resume reliably.
- Prevent duplicate timers.
- Do not keep the phone awake.
- Handle missing GPU instrumentation.
- Minimize battery impact.

## 2.6 Settings

Home Settings → System Monitor:

- Show System Monitor: ON by default.
- Refresh interval: 3 seconds by default.
- Show detailed units: ON by default.
- Persist across reboot.

Verify all four meters on the live phone.

---

# PHASE 3 — FIX WI-FI HARDWARE AND INTERNET

**CRITICAL PATH**

Inspect the actual S10+ WLAN chipset, kernel driver, firmware, rfkill state, NetworkManager, supplicant and device-tree initialization.

Identify the first failure in the bring-up chain.

Fix the actual adapter first, then the UI.

## Wi-Fi Settings

Implement:

- Wi-Fi ON/OFF.
- Live network scanning.
- SSID.
- Signal strength.
- Security type.
- Password input.
- Connect/disconnect.
- Saved networks.
- Forget networks.
- Automatic reconnection.
- Hidden SSIDs.
- IPv4/IPv6 information.
- Gateway, DNS and connection details.
- Clear error messages.

Support WPA2-Personal and WPA3-Personal where supported by the actual hardware/firmware/supplicant stack.

Investigate modern enterprise Wi-Fi separately.

Never silently weaken security.

Store credentials through the existing secure network-management mechanism.

Do not log passwords.

## Internet verification

Test independently:

1. Wi-Fi interface active.
2. Access point association.
3. Authentication.
4. IP address assignment.
5. Default route.
6. Gateway reachability.
7. DNS.
8. External connectivity.
9. HTTPS/TLS validation.
10. Browser page loading.

Differentiate connected Wi-Fi from working internet.

Correct the Quick Settings and status-bar indicators to reflect these separate states.

---

# PHASE 4 — NUXEL BROWSER

Create or finish a real Nuxel Browser using the existing WebKitGTK infrastructure.

Required functionality:

- Address bar.
- Back/forward.
- Reload/stop.
- Working tabs.
- New/close tab.
- Bookmarks.
- History.
- Downloads.
- Private browsing.
- Find in page.
- Real loading state.
- Correct HTTPS certificate validation.
- Error handling.
- Basic site permissions.
- Mobile/desktop preference where supported.
- Touchscreen scrolling.
- Keyboard compatibility.
- File Manager download integration.

Maintain sensible browser data isolation.

Do not expose privileged Nuxel APIs to ordinary webpages.

Browser must load actual HTTPS sites once Wi-Fi works.

Do not count a mock page or local placeholder as an internet test.

---

# PHASE 5 — FULL NUXEL FILE EXPLORER

Upgrade File Manager into a capable graphical file explorer.

**Default opening directory: the active user's actual home directory.**

Determine it from the logged-in account.

Never default to `/root` for an ordinary user.

## Navigation

Implement:

- Browse folders.
- Parent folder.
- Breadcrumbs.
- Back/forward.
- Home.
- Internal storage.
- Mounted external storage.
- Show hidden files.
- List/grid views.
- Sort by name, size, date and type.
- File-type icons.
- File information.
- Permissions and errors.

## File management

Implement:

- Open.
- Create folder.
- Rename.
- Copy.
- Cut.
- Paste.
- Move.
- Duplicate.
- Delete.
- Trash/restore where supported.
- Select one.
- Multi-select.
- Select all.
- Select none.
- Select files and folders together.
- Long-press selection.
- Context menu.
- Properties.
- Progress indicator.
- Conflict resolution.

Never overwrite files silently.

Handle partial operations and storage errors safely.

## Archives

Implement:

- ZIP creation.
- Extract here.
- Extract into named folder.
- Browse archive if practical.
- Progress and error feedback.
- Password support where the chosen library supports it.

Protect against ZIP path traversal, symlink escape, malicious archive expansion and unexpected overwrites.

Do not interpolate filenames unsafely into shell commands.

Ensure all functions are operable via touch.

Test real operations against the actual user's home directory.

---

# PHASE 6 — REAL AUDIO HARDWARE AND SOUND MODES

**CRITICAL PATH**

The Nuxel speaker has not yet produced owner-confirmed audible output.

Find and repair the hardware signal path rather than merely adjusting MP3-player code.

## 6.1 Audio bring-up

Inspect:

- ALSA card availability.
- Exynos ASoC.
- Samsung `beyond-madera` routing.
- CS47L93 codec.
- CS35L40 amplifier where applicable.
- DAPM paths.
- Mixer controls.
- Audio clocks/regulators.
- Firmware.
- PCM devices.
- PipeWire/WirePlumber if installed.
- UCM profiles.
- systemd audio services.
- Relevant kernel logs.

Do not guess dangerous codec or amplifier register settings.

Use safe low-volume tests.

Identify missing drivers or firmware precisely.

A successful `mpg123` exit does NOT prove the speaker works.

## 6.2 Sound cues

Repair:

- Nuxel boot MP3 plays once after boot animation → launcher handoff.
- Boot playback requests 44% software PCM gain, while respecting verified hardware safety limits.
- `nuxel-pow.mp3` plays immediately when actual volume changes occur.
- Volume preview uses the newly selected effective volume.
- Sounds do not overlap excessively.
- No replay of startup sound on every Home reload.

Preserve all working haptics.

## 6.3 Sound modes

Implement:

**Normal**
- Normal notification/system alert sounds.
- User-configurable media volume.
- Configured haptics.

**Vibrate**
- Audible notification/ringtone alerts muted.
- Vibration enabled for supported alerts.
- Separate media-volume policy.

**Silent**
- Notification/ringtone audio muted.
- Notification vibration muted except explicitly authorized exceptions.
- Media policy documented and independently controlled.

Do not imply cellular ringtone support is functional before modem/telephony integration.

## 6.4 Bell and status bar

Inspect whether the current bell icon means notifications or sound mode.

If it represents notification availability, preserve that purpose.

Add a separate status indicator for sound mode if necessary.

Show honest icons for Normal, Vibrate and Silent.

Add a Quick Settings tile and Sound Settings controls.

The indicator must reflect the actual selected system mode, not an unconfirmed UI state.

---

# PHASE 7 — BLUETOOTH

Identify the actual Bluetooth controller, firmware, HCI transport, kernel support and BlueZ status.

Repair initialization and pairing.

Implement:

- Bluetooth ON/OFF.
- Device scanning.
- Adapter status.
- Pair/unpair.
- Trust/untrust.
- Connect/disconnect.
- Saved devices.
- Reconnect.
- Passkey confirmation.
- Device-type display.
- Clear connection errors.
- Bluetooth Settings.
- Quick Settings integration.

Prioritize real support for:

- Speakers/headphones via A2DP.
- Supported hands-free audio.
- Keyboards.
- Mice.
- BLE devices.
- File transfers where OBEX support exists.

Do not claim universal compatibility without actual driver/profile support.

Test a real Bluetooth device.

Attempt Bluetooth speaker output as a separate diagnostic route from the physical phone speaker.

---

# PHASE 8 — NFC

Identify the actual S10+ NFC controller, available kernel drivers, firmware and Linux NCI interfaces.

Implement if supported:

- NFC enable/disable.
- Status reporting.
- Settings.
- Quick Settings tile.
- NDEF tag discovery/reading.
- Proper permissions.
- Useful errors.

Default NFC: OFF.

Do not claim payment, secure-element or card-emulation support without proven hardware and software capability.

Do not implement a fake switch.

If missing native Linux support, document the exact blocker.

---

# PHASE 9 — GPS, LOCATION AND NUXEL MAPS

## 9.1 Determine why the clock is correct

A synchronized clock does NOT prove GPS is active.

Inspect:

- RTC.
- Persisted system time.
- `timedatectl`.
- NTP services.
- Last successful time sync.
- Any GNSS-derived time source.

Document which source is actually supplying time.

## 9.2 GPS hardware

Identify available GNSS hardware interfaces and any dependency on Samsung modem firmware.

Investigate the native device nodes and services.

Use gpsd, GeoClue or other appropriate existing Linux infrastructure where suitable.

Implement:

- Location ON/OFF.
- Default OFF.
- Per-app location permissions.
- GPS fix status.
- Latitude/longitude.
- Accuracy.
- Fix timestamp.
- Available satellite information when exposed.
- Error reporting.
- No unnecessary background polling.

Never silently turn on GPS.

Never present IP geolocation as a verified GPS fix.

## 9.3 Nuxel Maps

Build a touch-friendly maps application based on OpenStreetMap data and suitable open-source rendering software.

Features:

- Map rendering.
- Touch pan/zoom.
- Pinch zoom.
- Current-location button.
- Accuracy circle.
- Coordinates.
- Search where a legitimate supported provider is configured.
- Markers.
- Optional directions via supported routing service.
- Dark/light appearance.
- Proper attribution.
- Location permissions.
- Offline cache or downloadable map regions where feasible.

Respect third-party tile usage policies.

Never assume online map tiles will work without internet.

Test real GNSS location separately from map display.

---

# PHASE 10 — CAMERA HARDWARE AND APPLICATION

Investigate the Exynos/Samsung camera subsystem.

Inspect:

- Rear/front camera sensors.
- Device tree.
- ISP drivers.
- Media-controller topology.
- V4L2 interfaces.
- Camera firmware.
- Sensor initialization.
- Existing Nuxel Camera implementation.

Achieve actual physical frame capture before declaring the camera functional.

Implement where hardware support permits:

- Live preview.
- Photo capture.
- Save to Pictures.
- Front/rear switching.
- Orientation correction.
- Gallery integration.
- Basic camera settings.
- Permission requests.

If proprietary firmware or kernel interfaces block capture, identify the exact missing component.

Do not fake live preview.

---

# PHASE 11 — HARDWARE BUTTON SHORTCUTS

Implement a single coherent input-event state machine.

Do not introduce competing event daemons.

## Double Power → Camera

Two rapid short Power presses launch Nuxel Camera.

Use a hardware-tested double-tap window around 350–450 ms.

Ensure:

- Single Power retains intended sleep/wake behavior.
- Long Power opens the power menu.
- Double Power does not accidentally blank the screen twice.
- Lock-screen permissions are respected.
- Repeated presses do not launch multiple camera instances.

## Double Bixby → Flashlight

Two rapid short Bixby presses toggle the physical flashlight.

Use the verified LED/torch driver interface.

Respect electrical/thermal safety.

Synchronize with the Flashlight Quick Settings tile.

Do not break other Bixby actions.

## Power + Volume Down → Screenshot

Capture the real current display.

Use the appropriate Wayland/Phoc screenshot or screencopy route.

Save to:

`~/Pictures/Screenshots/`

Use timestamped filenames and visible confirmation.

Correctly prioritize the chord over separate Power/Volume actions.

Verify the resulting PNG represents the current screen, not an old framebuffer.

## Input regression testing

Preserve:

- Back/Home/Recents.
- Long-press Back and Home.
- Volume adjustments.
- Navigation haptics.
- Keyboard haptics.
- Power sleep/wake.
- Power menu.
- Existing gestures.

Test key bounce, repeat events, simultaneous presses and timeout handling.

---

# PHASE 12 — STATUS BAR ICONS AND HONEST HARDWARE STATE

The current top bar reportedly shows an unusual Wi-Fi half-circle and mobile signal bars even though no SIM is installed.

Audit every indicator.

**A UI icon must report real hardware state, not decorative assumptions.**

## Wi-Fi

Represent:

- Disabled.
- Enabled/disconnected.
- Connecting.
- Connected locally.
- Connected without internet.
- Internet verified.
- Adapter unavailable.

Use supplied Nuxel assets and accurate signal strength when supported.

## Cellular

The device currently has no SIM installed.

Correct behavior may be:

- No SIM.
- Modem unavailable.
- SIM detected.
- Searching.
- Registered.
- Connected.
- Signal strength if genuinely provided.

Distinguish missing SIM from missing modem support.

Do not display fabricated registered-network signal bars.

## Sound mode

Display Normal/Vibrate/Silent accurately.

Do not reuse an existing notifications-only icon if that would create confusion.

## Other status indicators

Verify:

- Battery.
- Charging.
- Bluetooth.
- NFC.
- GPS/location.
- Wi-Fi.
- Cellular.
- Sound mode.
- Time.
- VPN where applicable.
- Notifications.

Every icon must correspond to actual system state.

Preserve and correctly render the owner-supplied PNG artwork.

Fix loading, sizing, transparency and cache issues.

Tapping indicators should open appropriate controls where supported.

---

# PHASE 13 — QUICK SETTINGS FULL FUNCTIONALITY

Repair and integrate actual backend control for:

- Wi-Fi.
- Bluetooth.
- Location.
- NFC.
- Flashlight.
- Normal/Vibrate/Silent.
- Cellular state.
- Relevant battery/power modes.

Every tile must:

1. Load the supplied icon asset.
2. Read the actual current state.
3. Perform a real supported operation.
4. Verify the operation succeeded.
5. Update the visible state.
6. Display honest unavailable/error states.

Do not implement toggles that only change CSS.

Repair the Quick Settings panel background and toggle artwork as described in Phase 1.

Ensure the shade continues to respond to the existing swipe gestures.

---

# PHASE 14 — PERFORMANCE, POWER AND SECURITY

Keep Nuxel practical on the Galaxy S10+.

Requirements:

- No excessive background polling.
- No unnecessary GPU-heavy UI effects.
- No high-frequency animation loops.
- No duplicate hardware handlers.
- No unnecessary wake locks.
- Respect system suspend/resume.
- No memory leaks.
- No unlimited logs.
- No blocking the main Home/UI thread.
- No privileged browser access.
- No arbitrary root-level File Manager operations.
- No plaintext logging of wireless credentials.
- No unrequested persistent GPS tracking.
- No network exposure of internal telemetry APIs.

Use existing D-Bus notifications and kernel event interfaces instead of continuous polling wherever practical.

Stop unused services when user-controlled features are disabled.

Preserve existing user data and settings.

---

# PHASE 15 — IMPLEMENTATION ORDER

Do not implement all features as one enormous unreviewable change.

Use milestones with separate commits, tests and deployment receipts.

## Milestone A — UI and foundation repair

1. Fix dock/panel backgrounds.
2. Fix custom icon loading.
3. Repair current service-worker/cache behavior.
4. Implement four live hardware meters.
5. Fix truthful status-bar icons.
6. Verify the launcher and navigation still function.

**Gate:** Owner sees correct pixel-art docks and continuously updating system telemetry.

## Milestone B — Connectivity

1. Repair Wi-Fi hardware.
2. Connect to a real network.
3. Verify DNS and HTTPS.
4. Complete Nuxel Wi-Fi Settings.
5. Build/finish Nuxel Browser.

**Gate:** Open a real HTTPS website in Nuxel Browser.

## Milestone C — Audio and devices

1. Repair ALSA/codec/amplifier route.
2. Verify speaker output.
3. Verify boot/volume cues.
4. Implement sound modes.
5. Repair Bluetooth.
6. Pair/test an available peripheral.

**Gate:** Owner hears real sound and can operate audio modes.

## Milestone D — Local applications

1. Complete File Explorer.
2. Test copy/move/selection operations.
3. Verify ZIP operations.
4. Integrate browser downloads.
5. Fix permissions and file dialogs.

**Gate:** Owner can manage real files through the touchscreen.

## Milestone E — Physical controls

1. Fix screenshots.
2. Implement double-Power camera shortcut.
3. Implement double-Bixby flashlight shortcut.
4. Repair the camera stack where possible.
5. Test all hardware button interactions.

**Gate:** Physical shortcuts reliably perform their intended operations without regressions.

## Milestone F — NFC, GPS and Maps

1. Investigate and repair NFC.
2. Repair location handling.
3. Default Location to OFF.
4. Implement Nuxel Maps.
5. Test real hardware location if available.

**Gate:** Supported hardware features operate correctly and unsupported interfaces are honestly marked unavailable.

If one hardware component is blocked by unavailable vendor drivers or firmware, document it precisely and continue with the next independent task.

Do not let the proprietary Samsung camera stack prevent completion of Wi-Fi, Browser, File Explorer or dock artwork.

---

# PHASE 16 — LIVE USB DEPLOYMENT

For every completed milestone:

1. Inspect the exact files changed.
2. Run tests.
3. Cross-compile or build for Linux ARM64 as necessary.
4. Confirm binaries target the actual S10+ architecture.
5. Back up existing deployed files.
6. Stage the new files atomically where feasible.
7. Deploy through the existing live USB console.
8. Verify hashes against source artifacts.
9. Restart only affected services.
10. Verify that the live phone is actually running the updated software.
11. Inspect logs.
12. Test the feature.
13. Request physical owner testing when necessary.
14. Roll back immediately if an essential service fails.

Avoid rebuilding or reflashing the entire image when a safe userspace update is sufficient.

## Prevent stale UI deployments

For the launcher, icons and dock backgrounds:

- Verify the active webroot.
- Verify actual deployed asset URLs.
- Verify CSS and JavaScript versions.
- Bust stale WebKit caches safely.
- Update service-worker versions where required.
- Confirm computed styles and rendered output.
- Confirm the latest files are genuinely loaded.

This step is mandatory because previous Nuxel patches installed the correct assets but they did not appear on the phone.

---

# PHASE 17 — 90-SECOND PHYSICAL TEST WINDOWS

Announce test windows whenever owner interaction is required.

Capture logs during the test.

### Visual test

Ask the owner to:

- Inspect bottom navigation dock artwork.
- Inspect application dock backgrounds.
- Open Quick Settings.
- Verify toggle icons.
- Switch between Home desktops.
- Confirm custom panels remain visible.
- Observe the four live meters.
- Turn the meters off/on in Home Settings.

### Connectivity test

Ask the owner to:

- Enable Wi-Fi.
- Join an available network.
- Open Nuxel Browser.
- Navigate to a real HTTPS website.
- Confirm the connectivity icon changes correctly.

### Audio and Bluetooth test

Ask the owner to:

- Increase/decrease volume.
- Confirm `nuxel-pow.mp3` is audible.
- Test the physical speaker.
- Switch Normal/Vibrate/Silent.
- Confirm correct icon.
- Pair a Bluetooth device if available.
- Confirm actual audio output if using a speaker.

### Storage test

Ask the owner to:

- Open File Explorer.
- Navigate from the home folder.
- Create a folder.
- Select multiple items.
- Copy/paste/move.
- Create and extract a ZIP.
- Confirm final files and folders.

### Hardware shortcut test

Ask the owner to:

- Double-tap Power.
- Double-tap Bixby.
- Press Power + Volume Down.
- Check camera, flashlight and screenshot behavior.

### GPS/NFC test

Ask the owner to:

- Enable location.
- Open Nuxel Maps.
- Confirm whether a real GNSS fix is acquired.
- Turn location off.
- Toggle NFC.
- Test an NFC tag if available.

Do not assume success if the owner hasn't confirmed the physical outcome.

For failures, collect logs, determine the fault, patch and repeat the relevant test.

---

# PHASE 18 — ACCEPTANCE REPORT

Produce a complete results matrix.

| Component | Software | Hardware | Evidence | Blocker |
|---|---|---|---|---|
| Bottom navigation dock background | | | | |
| App dock background | | | | |
| Quick Settings backgrounds | | | | |
| Custom icon loading | | | | |
| CPU utilization/frequency | | | | |
| RAM utilization/quantity | | | | |
| GPU utilization/frequency | | | | |
| GPU shared-memory usage | | | | |
| Wi-Fi adapter | | | | |
| Wi-Fi Settings | | | | |
| Internet connectivity | | | | |
| Nuxel Browser | | | | |
| File Explorer | | | | |
| ZIP operations | | | | |
| Speaker/audio routing | | | | |
| Boot and volume audio | | | | |
| Normal/Vibrate/Silent | | | | |
| Bluetooth | | | | |
| NFC | | | | |
| GPS | | | | |
| Nuxel Maps | | | | |
| Camera | | | | |
| Flashlight | | | | |
| Screenshot | | | | |
| Hardware shortcuts | | | | |
| Status-bar indicators | | | | |
| Quick Settings | | | | |

Include:

- Modified source files.
- Build results.
- Automated tests.
- Device service status.
- Hardware diagnostics.
- Actual deployed file paths.
- Git commits.
- Screenshot/image-render evidence where obtainable.
- Deployment receipts.
- Rollback information.
- Explicit owner-confirmed results.
- Outstanding hardware blockers.

Use `BLOCKED` or `UNVERIFIED` rather than claiming completion if genuine hardware evidence is missing.

---

# NON-NEGOTIABLE QUALITY RULES

1. No fake system metrics.
2. No fake GPU VRAM.
3. No fake network connectivity.
4. No fake SIM signal bars.
5. No claiming GPS works because the clock is correct.
6. No claiming speaker playback works because a decoder exits successfully.
7. No claiming camera works without actual physical frames.
8. No pretend Quick Settings toggles.
9. No unimplemented File Explorer buttons.
10. No replacing owner-supplied pixel-art assets with placeholders.
11. No saying dock backgrounds work merely because PNG files exist.
12. No accepting a patch when an old WebKit cache still displays the previous UI.
13. No breaking the existing touchscreen, gestures, navigation, boot or display stack.
14. No unsafe bootloader, recovery, partition or kernel modification.
15. No giant untested commit mixing all subsystems.
16. No declaring the mission finished with outstanding tests silently skipped.

**EVERY WORKING FEATURE MUST BE VERIFIED AT THE LEVEL APPROPRIATE TO IT: source → build → deployment → system integration → physical behavior.**

---

# FINAL EXECUTION INSTRUCTION

Begin with an actual repository and live-phone audit.

Then execute Milestone A immediately, prioritizing:

1. Broken dock backgrounds.
2. Broken custom artwork loading.
3. Four genuinely live CPU/RAM/GPU/GPU-memory meters.
4. Status-bar hardware indicators.

Deploy these fixes to the live S10+ and obtain actual rendered-screen confirmation before advancing to connectivity.

Then progress through Wi-Fi, Browser, Audio, Bluetooth, File Explorer, hardware buttons, Camera, NFC, GPS and Maps.

Keep checkpointing. Continue to the next unblocked task. Repair failures instead of hiding them.

**SUCCESS MEANS NUXEL LOOKS LIKE NUXEL, REPORTS REAL HARDWARE STATE, AND ACTUALLY WORKS AS A LINUX PHONE.**

**GO BUILD THE PHONE. 🐧🔥**
