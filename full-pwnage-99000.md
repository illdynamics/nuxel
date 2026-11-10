# full-pwnage-99000.md — Nuxel USB-C HDMI: Complete External Display, Mirroring, Separate Desktop, Orientation and HDMI Audio Implementation

## 0. Mission

Perform a complete source-driven investigation, implementation, deployment, and physical-device verification of USB-C-to-HDMI functionality on Nuxel.

Target device:

- Device: Samsung Galaxy S10+
- Model: SM-G975F
- Codename: `beyond2lte`
- SoC: Samsung Exynos 9820
- OS: Nuxel, Fedora-based ARM64 mobile Linux
- Repository: inspect the current checkout; do not assume the working directory or branch.
- Deployment scripts: inspect `./scripts`.
- Current hardware state: **the USB-C-to-HDMI connection is already connected to the phone. Use this live connection as the primary test target.**

The user has already connected an external display, but HDMI output has not been established as a properly functioning Nuxel feature. The implementation must go beyond detecting a connected monitor.

Deliver a complete external-display experience with:

1. Reliable USB-C/DisplayPort Alt Mode and HDMI output handling, to the extent supported by the device hardware and current kernel.
2. Functional screen mirroring.
3. Functional independent external desktop.
4. Correct display orientation and geometry in both modes.
5. An actionable Nuxel notification when an external display is connected, allowing the user to choose mirroring or a separate desktop.
6. Correct display disconnection, reconnection, and mode restoration behavior.
7. Working HDMI audio, physically verified through the connected display.
8. Proper integration with the existing Nuxel UI, compositor, display pipeline, audio system, settings, and input management.
9. Regression-free operation of the internal display and normal phone interaction.

**Do not stop after discovering why HDMI does not work. Fix it. Do not stop after implementing code. Deploy it. Do not stop after deployment. Physically verify the external display and audio.**

The final outcome must be based on evidence from the actual S10+ and the currently connected display.

---

# 1. Non-negotiable execution requirements

## 1.1 Work all the way through

Follow this sequence:

1. Inspect repository, branch, uncommitted changes, and existing architecture.
2. Inspect the currently connected HDMI hardware and active system state.
3. Trace the complete display path.
4. Identify the actual failure point.
5. Design the smallest correct architectural solution.
6. Implement the required changes.
7. Add tests and diagnostics.
8. Build and run automated tests.
9. Deploy using a verified existing deployment workflow.
10. Test on the actual connected HDMI display.
11. Verify mirroring and separate-desktop mode.
12. Verify orientation changes.
13. Verify HDMI audio through the external display.
14. Perform a real disconnect/reconnect test.
15. Verify the connection notification and both mode-selection actions.
16. Test regressions and recovery.
17. Write the final report.

Do not substitute a plan for implementation.

Do not mark a feature complete because a service starts, a connector is detected, an API returns success, or a configuration file contains the expected value.

## 1.2 Current HDMI connection is the test environment

The USB-C-to-HDMI adapter/cable and external display are currently connected.

Preserve that setup.

Before changing anything, record the initial state:

- USB-C connection state.
- DisplayPort Alt Mode state, if observable.
- Type-C port and mux state, if exposed.
- HPD (Hot Plug Detect) state.
- DRM connector state, if available.
- Connector name and status.
- EDID availability and validity.
- Supported modes and preferred mode.
- Current display resolution and refresh rate.
- Current orientation.
- External display power/connection state.
- Current compositor and display backend.
- Framebuffer and DRM device state.
- Active audio devices and routes.
- Current PipeWire/WirePlumber or other audio service state.
- Relevant kernel logs.
- Relevant service logs.

Capture a baseline before restarting services or changing configuration.

Do not disconnect the cable simply to reproduce the initial problem. Use the currently connected state first.

If a restart becomes necessary, explain why, preserve remote access, and make the restart as narrowly scoped as possible.

## 1.3 Never fabricate physical verification

Maintain a distinction between:

- Source inspected.
- Automated test passed.
- Build passed.
- Service started.
- Hardware detected.
- External image physically observed.
- Mirroring physically verified.
- Separate desktop physically verified.
- Orientation physically verified.
- HDMI audio physically heard.
- Reconnection physically verified.

Only report the level actually demonstrated.

If the agent cannot physically observe the external display or hear its speakers, it must not claim those tests passed. Find a practical verification method or report the precise remaining limitation.

---

# 2. Safety and architecture preservation

Nuxel is a custom mobile Linux operating system. Do not assume that it uses a conventional desktop graphics stack or that a generic Linux desktop solution will work.

The implementation must respect the actual deployed architecture.

## 2.1 Preserve the existing display architecture

Historically, Nuxel has used a Wayland-based display path involving Phoc, framebuffer presentation, and a dedicated framebuffer bridge. However, this is historical context, not permission to assume the current architecture.

Inspect what is actually running.

Determine:

- Which compositor is active.
- Whether Phoc is still the active compositor.
- Whether the compositor has DRM/KMS access.
- Whether the phone's internal display is exposed through DRM, framebuffer, or another backend.
- Whether `/dev/fb0` is used.
- Whether a framebuffer bridge is active.
- Whether `/dev/dri` devices exist.
- Which process owns each display device.
- How surfaces are composed and presented.
- Whether external outputs can be managed by the existing compositor.
- Whether the current implementation supports multiple outputs at all.

**Do not introduce a second writer to `/dev/fb0`.**

Do not replace the compositor just to obtain HDMI output.

Do not switch to llvmpipe or software rendering as a workaround.

Do not blindly set generic `WLR_*` environment variables.

Do not globally change the phone's resolution, DPI, or framebuffer configuration to force an external display to work.

Do not bypass the active compositor with an independent process that competes for display ownership.

If the current graphics architecture cannot support multiple displays, establish the exact limitation and implement the smallest compatible extension. Any kernel or driver limitation must be supported by evidence.

## 2.2 Preserve the internal phone display

The built-in AMOLED display must continue to work normally.

All changes must preserve:

- Phone display output.
- Touch input.
- Existing navigation buttons.
- Home, Back, and Tabs behavior.
- Lock screen.
- Quick Settings and status bar.
- App windows and fullscreen behavior.
- Existing orientation handling.
- Existing compositor lifecycle.
- Normal screen blanking and wake behavior.

An HDMI fix that breaks the phone's internal display is not an acceptable fix.

## 2.3 Safe deployment

Inspect `./scripts` before deployment.

Identify:

- The canonical Nuxel deployment script.
- Whether a targeted service/UI deployment exists.
- Whether the script builds locally or on-device.
- Whether it restarts the compositor.
- Whether it reboots the phone.
- Whether it overwrites configuration or user data.
- Whether it can deploy only the affected components.
- Whether it has a rollback procedure.

Do not execute an unfamiliar script without inspecting it.

Prefer the smallest deployment scope.

Do not flash the bootloader, recovery, modem, firmware, or kernel for a userspace issue.

If a kernel or driver change is conclusively necessary, first document why userspace cannot solve it, identify the exact required change, and preserve a recovery route. Do not perform a firmware or kernel flash as an unapproved shortcut.

---

# 3. Initial repository and runtime investigation

## 3.1 Repository inventory

Inspect:

- Git root and active branch.
- Working-tree changes.
- Existing HDMI-related code.
- USB-C and Type-C handling.
- Display manager and compositor integrations.
- Output enumeration.
- Orientation and rotation handling.
- Notification system.
- Quick Settings.
- Settings application.
- Input routing.
- Audio routing.
- Existing hardware diagnostics.
- Existing device deployment scripts.

Search for relevant concepts, including:

- `hdmi`
- `displayport`
- `dp-alt`
- `typec`
- `usb-c`
- `hotplug`
- `hotplugged`
- `HPD`
- `EDID`
- `drm`
- `connector`
- `kms`
- `output`
- `monitor`
- `external display`
- `mirror`
- `clone`
- `extend`
- `desktop`
- `orientation`
- `rotation`
- `PipeWire`
- `WirePlumber`
- `ALSA`
- `ELD`
- `HDMI audio`

Do not assume the search terms reveal the whole implementation. Follow actual call paths.

## 3.2 Live device inspection

Connect to the currently connected S10+ using the supplied access method where appropriate:

```bash
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167
```

Preserve host-key verification. Do not use `StrictHostKeyChecking=no`.

Verify that the target is actually the intended S10+ before running any modifying operation. If the connection fails, report that fact and inspect the repository locally; do not silently substitute another device.

Collect useful diagnostic information, adapting commands to the device:

```bash
uname -a
cat /etc/os-release
systemctl --failed
systemctl list-units --type=service --state=running
ls -l /dev/fb*
ls -l /dev/dri 2>/dev/null
ls -l /dev/snd 2>/dev/null
lsusb
dmesg
```

Inspect available DRM connector state, if present:

```bash
find /sys/class/drm -maxdepth 2 -type f -print
```

For each available connector, inspect:

- `status`
- `enabled`
- `modes`
- `edid`
- `dpms`, if exposed
- `link_status`, if exposed
- connector-specific properties

Inspect relevant Type-C and USB state:

```bash
find /sys/class/typec -maxdepth 4 -type f -print 2>/dev/null
find /sys/bus/usb/devices -maxdepth 3 -type f -print 2>/dev/null
```

Do not assume all these paths exist. Absence is useful diagnostic evidence.

Inspect relevant kernel messages:

```bash
dmesg | grep -Ei 'typec|usb|displayport|drm|hdmi|hpd|edid|decon|dpu|exynos|audio|asoc|snd'
```

Inspect audio:

```bash
aplay -l
aplay -L
cat /proc/asound/cards
cat /proc/asound/pcm
```

Inspect PipeWire and WirePlumber state if installed:

```bash
systemctl --user status pipewire pipewire-pulse wireplumber
wpctl status
```

Use the correct user/session context. Do not assume root's user services represent the logged-in desktop audio session.

Capture the results in a diagnostic report.

## 3.3 Establish the actual hardware display path

Trace the full signal path:

USB-C connector
→ Type-C controller
→ DisplayPort Alt Mode negotiation
→ orientation/mux switching
→ DisplayPort link
→ HDMI adapter/conversion
→ hotplug detection
→ EDID read
→ display mode selection
→ display controller/DRM/KMS or active presentation backend
→ compositor output
→ external monitor.

Determine which stages are present and which are failing.

The S10+ may expose some of these stages through kernel interfaces, device-tree configuration, vendor drivers, or logs rather than standard Linux interfaces.

Do not infer that DisplayPort Alt Mode works merely because USB data works or the adapter is physically attached.

Do not infer that the HDMI adapter works merely because the phone reports a Type-C device.

Do not infer that the display works because an EDID can be read.

If the adapter negotiates DisplayPort but the display controller cannot drive an external output, identify that boundary precisely.

---

# 4. Identify and fix the root cause

Build an evidence-based diagnosis.

Potential failure categories include, but are not limited to:

1. USB-C Type-C controller does not detect or negotiate the expected mode.
2. DisplayPort Alt Mode negotiation is not occurring.
3. Type-C orientation or mux configuration is incorrect.
4. HPD is not detected or propagated.
5. EDID cannot be read.
6. EDID is read but mode selection fails.
7. DisplayPort link training fails.
8. External output is unsupported by the active display controller driver.
9. DRM/KMS output exists but the compositor does not enumerate it.
10. The compositor enumerates the output but disables it.
11. The framebuffer bridge only supports the internal display.
12. The display is configured but the external buffer is not presented.
13. Resolution, refresh rate, rotation, or scaling is invalid.
14. The external display is active but the application/window layout is incorrect.
15. HDMI audio is not exposed by the kernel audio driver.
16. HDMI audio is exposed but not selected by PipeWire/WirePlumber.
17. The HDMI adapter or display does not expose audio capabilities correctly.

These are hypotheses, not conclusions.

For every diagnosed failure:

- Identify the exact source or runtime component.
- Show the relevant logs, state, or code path.
- Explain why it prevents the desired behavior.
- Implement a targeted correction.
- Add a regression test or diagnostic where possible.
- Verify the correction on the actual hardware.

Do not paper over a failed lower-level stage with a UI toggle that pretends HDMI is active.

---

# 5. External display architecture

Implement a coherent display-management layer rather than separate disconnected fixes for mirroring, desktop mode, orientation, and notification behavior.

First inspect whether Nuxel already has a display manager or output-management abstraction. Extend it if appropriate. Avoid duplicating an existing authority.

The resulting architecture must provide a single authoritative representation of:

- Internal display.
- External display(s), if supported.
- Connection state.
- Output capabilities.
- Selected mode.
- Resolution and refresh rate.
- Physical dimensions, when available.
- Logical dimensions.
- Scale factor.
- Rotation/orientation.
- Position in the desktop coordinate space.
- Active output state.
- Input association.
- Audio association.

A suggested conceptual model:

```text
DisplayManager
 ├── InternalDisplay
 ├── ExternalDisplay[]
 ├── ConnectionMonitor
 ├── CapabilityDiscovery
 ├── ModeSelector
 ├── LayoutManager
 ├── OrientationManager
 ├── InputRouter
 └── DisplayModeController
```

This is a conceptual architecture, not a requirement to create classes with these exact names. Follow the repository's existing conventions.

## 5.1 Connection lifecycle

Support an explicit lifecycle:

```text
DISCONNECTED
    ↓
CONNECTING
    ↓
DETECTING_CAPABILITIES
    ↓
AVAILABLE
    ↓
MODE_SELECTION_PENDING
    ↓
MIRRORING or SEPARATE_DESKTOP
    ↓
DISCONNECTING
    ↓
DISCONNECTED
```

Handle:

- Cable insertion.
- Cable removal.
- Adapter insertion.
- Display power-off.
- Display power-on.
- Temporary HPD loss.
- EDID read failures.
- Link training failures.
- Display mode changes.
- Orientation changes.
- Compositor restarts.
- Audio device appearance/disappearance.
- Reconnection after a previous session.

Avoid rapid notification spam or duplicate display objects.

Use event-driven state updates rather than arbitrary sleeps.

Debounce genuinely noisy hardware events, but do not hide slow or failed negotiation behind long fixed delays.

## 5.2 Multiple outputs

If the hardware and active driver expose multiple display outputs, manage them through the existing supported graphics stack.

If only one external output is supported, make that limitation explicit.

Do not claim multi-monitor support simply because the UI has multiple display entries.

The built-in phone screen must remain the primary display and must not be accidentally disabled when an external display is activated.

---

# 6. Connection notification and mode selection

Whenever an external HDMI display is newly connected, Nuxel must show an actionable notification.

This is a required feature, not an optional polish item.

## 6.1 Notification behavior

Show a clear notification such as:

**External display connected**

Choose how to use the connected display:

- **Mirror screen**
- **Separate desktop**

The notification must be integrated with Nuxel's actual notification system.

Do not create a parallel notification implementation or a disconnected popup that bypasses notification persistence and lifecycle handling.

The notification must:

- Identify the external display where a useful name is available.
- Explain that an external display is available.
- Present both mode actions.
- Work from the normal desktop and while an application is fullscreen.
- Be accessible through the notification center if it is not immediately acted upon.
- Avoid duplicate notifications for repeated low-level events during a single connection.
- Reappear after a genuine disconnect and subsequent reconnect.
- Remain usable if the display takes time to become ready.

Do not display the mode-selection notification for the internal display.

Do not display it continuously while the cable remains connected.

## 6.2 Mode selection semantics

The two actions must perform real operations.

**Mirror screen** must configure a real mirrored output.

**Separate desktop** must configure a real independent external workspace.

Do not implement buttons that merely change a saved preference or update a label.

The notification actions must invoke the canonical display manager and report failure if configuration fails.

## 6.3 Reconnection and remembered preference

On every new physical connection, present the choice again.

The system may remember the last selected mode as a suggested/default option, but it must not silently suppress the notification or assume the previous mode is always wanted.

If the user selects a mode:

- Apply it.
- Persist the preference appropriately.
- Record the selected mode for diagnostics.
- Restore the phone to a safe internal-only configuration when the external display disconnects.

If the user dismisses the notification without selecting a mode, leave the phone's internal display operating normally. Do not unexpectedly disable the internal display or switch into an unusable state.

If mode configuration fails, show a useful error notification and retain a working internal display.

## 6.4 Settings integration

Add or extend the existing display settings only if necessary.

Provide access to:

- Current external display state.
- Current mode.
- Switch between Mirror and Separate Desktop while connected.
- Supported resolution and refresh rate.
- Orientation behavior.
- Audio output selection, if needed.
- Restore defaults or safely return to internal-only mode.

Do not add a redundant settings page if an existing display settings section is the correct location.

---

# 7. Mirroring mode

Mirroring must display the phone's actual composed screen on the external display.

It must not be a static screenshot, a second unrelated desktop, or a UI-only simulation.

## 7.1 Required behavior

When the user chooses Mirror screen:

- Keep the phone's built-in display active.
- Show the same desktop/application composition on the external display.
- Preserve application content.
- Preserve status/navigation behavior as supported by the architecture.
- Handle fullscreen applications.
- Handle lockscreen and unlock transitions safely.
- Handle display rotation.
- Handle external mode/resolution changes.
- Recover cleanly if the HDMI link temporarily drops.

## 7.2 Resolution and scaling

Do not assume that the phone's internal resolution is the correct external resolution.

Read the external display's actual supported modes and select an appropriate mode.

Consider:

- EDID preferred mode.
- Supported resolutions.
- Supported refresh rates.
- Pixel clock and link limitations.
- Aspect ratio.
- Internal rendering dimensions.
- External output dimensions.
- Scaling quality.
- Performance and memory bandwidth.

Avoid stretching the phone image into an incorrect aspect ratio.

Maintain the correct aspect ratio and use a deliberate scaling policy.

If letterboxing or pillarboxing is necessary, center the content cleanly.

Do not globally change the phone display resolution to make mirroring work.

## 7.3 Performance

The implementation must avoid unnecessary full-screen copies and repeated expensive composition.

Inspect whether the active graphics stack supports:

- Shared buffers.
- Direct scanout.
- Hardware composition.
- Multi-output rendering.
- Zero-copy buffer sharing.

Use the most efficient supported path.

Do not claim zero-copy unless the actual path demonstrates it.

Monitor CPU, memory, GPU/compositor load, frame pacing, and visible tearing during live testing.

The external output must be usable without making the phone's own UI unusably slow.

---

# 8. Separate desktop mode

Separate desktop mode must provide a genuinely independent workspace on the HDMI display.

It is not sufficient to show the phone desktop on a different resolution.

## 8.1 Required behavior

When the user chooses Separate desktop:

- Keep the phone display active.
- Keep the phone's existing desktop usable.
- Create an independent external desktop/workspace.
- Allow windows to be placed on the external display.
- Allow supported applications to open or move to the external display.
- Keep the phone and external desktop state independent where appropriate.
- Preserve window focus and input routing.
- Handle external display disconnection without losing application state.

The internal display must not become blank or unusable.

## 8.2 Window management

Inspect the current Nuxel window-management architecture.

Implement or extend output-aware window placement.

At minimum:

- Track which output owns a window.
- Track the output's logical geometry.
- Place new windows according to a sensible policy.
- Allow windows to move between outputs if the compositor supports it.
- Ensure fullscreen applications fullscreen on the intended output.
- Avoid windows appearing outside all visible output boundaries.
- Ensure the launcher and desktop are rendered on the intended display.
- Restore windows when the external display disappears.

If a particular application cannot move between outputs because of a compositor or toolkit limitation, document the exact limitation and provide the best supported behavior.

## 8.3 Pointer and touch routing

Separate desktop mode must have usable input.

Inspect:

- Touchscreen device ownership.
- Pointer devices.
- Mouse and keyboard devices.
- Wayland seats.
- Input focus.
- Output layout.
- Touch coordinate transformation.
- Input-region calculations.

The phone's touchscreen must continue to work on the phone.

If an external mouse is connected, it should be possible to interact with the external desktop where supported.

Do not route all phone touchscreen events to the external display.

Do not invent touchscreen support on an HDMI monitor that has no touch hardware.

If an external touchscreen is connected and supported, map its coordinates to the correct external output.

Ensure pointer movement, focus, and window activation are consistent with the actual desktop geometry.

## 8.4 Desktop presentation

Use Nuxel's existing visual language and desktop components.

Do not create a generic desktop shell that conflicts with Nuxel's interface.

Use the existing launcher, panel, window decorations, and app integration where appropriate.

The external desktop should be comfortable at typical monitor and TV resolutions.

Ensure:

- No clipped panel or dock.
- No off-screen window placement.
- No phone-sized UI stretched across a large display.
- No unexpected portrait layout on a landscape monitor.
- No duplicate input-blocking surfaces.
- No stale surfaces after changing modes.

---

# 9. Orientation and rotation

Orientation must be treated as a first-class display property.

The external display must not inherit an incorrect orientation simply because the phone rotates, and the phone must not be forced into an unsuitable orientation because the HDMI display is connected.

## 9.1 Separate orientation state

Distinguish:

1. Physical orientation of the phone.
2. Logical orientation of the phone UI.
3. Physical orientation of the external monitor or TV.
4. Logical orientation of the external desktop.
5. Rotation and transformation applied by the compositor.
6. Application-specific orientation requirements.

Do not collapse these into one global orientation variable.

## 9.2 Mirroring orientation

In Mirror mode:

- Preserve the phone's actual logical orientation.
- Reflect that screen composition correctly on the external display.
- Handle phone portrait-to-landscape rotation.
- Handle landscape-to-portrait rotation.
- Recalculate scaling and letterboxing after rotation.
- Avoid stretching or cropping.
- Avoid stale buffers from the previous orientation.
- Avoid black frames or a prolonged broken layout.

The external display should show the same logical screen composition, appropriately fitted to its own mode.

A landscape TV should not force the phone UI into landscape if the phone is being used in portrait, unless the actual mirroring design explicitly requires and correctly implements that transformation.

## 9.3 Separate-desktop orientation

In Separate desktop mode:

- The external desktop should default to the display's natural/preferred orientation, generally landscape for a normal TV or monitor.
- The phone should retain its own orientation behavior.
- Rotating the phone should not rotate the external desktop.
- Changing the external display's orientation should not rotate the phone UI.
- If the display is physically portrait-mounted and its EDID or system configuration exposes rotation information, respect it.
- Provide a safe manual rotation option if automatic detection is not available.

Do not pretend that a normal HDMI TV communicates its physical mounting orientation if it does not.

If the physical orientation cannot be detected, use a sensible default and expose a manual setting.

## 9.4 Rotation implementation

Inspect the compositor's supported output-transform API and use it.

Do not rotate the framebuffer globally if only the external output needs rotation.

Do not apply rotation twice.

Ensure that output geometry, damage tracking, touch transforms, pointer coordinates, and window layout all agree.

Test:

- Phone portrait + external landscape.
- Phone landscape + external landscape.
- Phone portrait + external portrait, if available.
- External display rotation setting changed while connected.
- Rotation while an application is fullscreen.
- Rotation while a window is being moved.
- Rotation while in mirroring mode.
- Phone rotation while in separate-desktop mode.

---

# 10. HDMI audio: mandatory implementation

HDMI audio is a core acceptance requirement.

The user must be able to hear Nuxel audio through the connected TV or monitor.

A visible HDMI picture without working HDMI audio is incomplete.

## 10.1 Trace the audio hardware path

Investigate the full audio path:

USB-C DisplayPort/HDMI adapter
→ display audio capability advertisement
→ EDID audio blocks
→ kernel audio driver
→ ALSA card/PCM device
→ ELD/connector association, where available
→ PipeWire/WirePlumber or active sound server
→ selected output route
→ HDMI display speakers or audio output.

Determine whether the adapter and monitor advertise audio support.

Inspect relevant hardware and software state.

Useful diagnostics may include:

```bash
aplay -l
aplay -L
cat /proc/asound/cards
cat /proc/asound/pcm
wpctl status
pactl list cards
pactl list sinks
```

Inspect kernel messages related to HDMI, DP audio, ALSA, ASoC, codec, and ELD.

Adapt these commands to the actual installed stack.

Do not assume the S10+ exposes HDMI audio through a conventional desktop HDMI codec. Identify the actual Exynos and Samsung audio integration.

## 10.2 Audio device discovery

When HDMI connects:

- Detect whether the external display advertises audio support.
- Detect whether the kernel exposes a corresponding audio device or route.
- Expose the HDMI output through the active audio system when supported.
- Associate it with the correct external display.
- Make the output selectable.
- Avoid creating duplicate or phantom audio devices.
- Handle audio device appearance after display negotiation.
- Handle the audio device disappearing on HDMI disconnect.

If the audio device is not exposed by the kernel, identify whether the blocker is hardware, driver, device tree, codec routing, or userspace.

Do not fabricate an ALSA device or create a dummy sink and call that HDMI audio.

## 10.3 Audio routing behavior

When HDMI audio is available, the user should be able to route audio to the external display.

Implement sensible behavior:

- When the user chooses HDMI audio, route normal Nuxel application audio to it.
- Preserve the ability to switch back to the phone speaker or Bluetooth.
- Avoid forcibly changing the audio route when HDMI is connected unless the user has explicitly configured that behavior.
- If the selected HDMI output disappears, safely fall back to the previous valid output.
- Do not leave the sound system stuck on a disconnected device.
- Avoid changing the phone's microphone route unnecessarily.

Integrate with Nuxel's existing sound settings and sound daemon rather than creating a competing audio manager.

## 10.4 Physical audio verification

On the connected HDMI display:

1. Confirm that the external audio device is detected.
2. Select the HDMI output.
3. Play a safe, moderate-volume test tone.
4. Play normal Nuxel application audio.
5. Confirm that sound is actually heard from the external display's speakers or audio output.
6. Verify that the phone's speaker remains selectable.
7. Disconnect HDMI and confirm safe audio fallback.
8. Reconnect and verify HDMI audio can be selected again.

Use a moderate volume. Do not generate loud test tones.

A successful `aplay` exit code is not proof of physical audio output.

A visible PipeWire sink is not proof of physical audio output.

If physical hearing/observation is unavailable, mark the test as unverified and state exactly what was established.

---

# 11. Display and audio user experience

Integrate the implementation into Nuxel's existing interface.

Do not create a visually unrelated HDMI application.

## 11.1 Notification

The connection notification must be actionable and reliable.

Example:

**External display connected**

`Samsung TV · 1920 × 1080 · 60 Hz`

- Mirror screen
- Separate desktop

Optional secondary action:

- Display settings

Only display monitor details that were actually detected.

Do not invent a brand, resolution, refresh rate, or audio capability.

## 11.2 Active connection indicator

When an external display is active, provide a sensible indicator in the existing status or Quick Settings interface if the existing design supports it.

The indicator should allow the user to access display mode/settings without navigating deeply.

Do not clutter the status bar.

## 11.3 Settings

The display settings must accurately reflect:

- Connected/disconnected state.
- External display identity.
- Selected display mode.
- Available modes.
- Active resolution and refresh rate.
- Orientation.
- Audio availability and selected output.

If the system cannot expose a setting reliably, do not display a fake control.

## 11.4 Error handling

If connection or configuration fails, explain the failure in useful language.

Examples:

- External display detected, but no supported display mode could be selected.
- DisplayPort link is not ready.
- HDMI audio is not available from the current adapter/display.
- Separate desktop is unavailable because the active display backend does not support multiple outputs.

Use the actual failure reason where available.

Keep the phone usable.

---

# 12. Hotplug and reconnection testing

A major requirement is that the next time HDMI is connected, Nuxel offers the mode choice.

Test a complete physical connection lifecycle.

## 12.1 Required test

With the display connected:

1. Confirm current display state.
2. Select Mirror mode.
3. Verify the picture.
4. Select Separate desktop mode.
5. Verify the independent workspace.
6. Verify orientation behavior.
7. Verify HDMI audio.
8. Disconnect the USB-C HDMI adapter/cable.
9. Confirm the external display is removed from the display manager.
10. Confirm the internal display remains usable.
11. Confirm external windows and surfaces are safely recovered.
12. Confirm HDMI audio disappears and routing falls back correctly.
13. Reconnect the adapter/cable.
14. Wait for real hardware negotiation and capability discovery.
15. Confirm a new actionable mode-selection notification appears.
16. Choose Mirror mode and verify it.
17. Disconnect and reconnect again if needed.
18. Choose Separate desktop mode and verify it.

Do not simulate a disconnect by merely toggling a software variable.

Do not claim reconnection passed unless the physical cable/adapter was actually disconnected and reconnected.

## 12.2 Rapid and unstable connections

Where possible, test:

- Quick disconnect/reconnect.
- Display power-off/on while connected.
- Adapter briefly losing connection.
- Unsupported or invalid EDID.
- Audio device appearing later than video.
- Mode change while connected.

Ensure that stale events do not create duplicate outputs or notifications.

Use event sequencing or connection-generation identifiers if necessary to reject stale asynchronous work.

---

# 13. Display mode and capability handling

## 13.1 EDID and supported modes

Parse and validate the actual EDID.

Record:

- Display identity, if available.
- Preferred mode.
- Supported modes.
- Refresh rates.
- Physical dimensions, if provided.
- Audio capability blocks, if provided.

Treat EDID as untrusted hardware input.

Handle missing, malformed, or incomplete EDID safely.

Do not hardcode a particular TV's resolution as the only supported mode.

## 13.2 Mode selection

Select a mode that is:

- Supported by the external display.
- Supported by the active display controller/driver.
- Within link bandwidth and hardware constraints.
- Appropriate for the display's preferred mode.
- Stable for the current graphics pipeline.

Provide a fallback mode when the preferred mode fails.

Do not force unsupported 4K or high-refresh modes.

Do not claim a mode is supported just because it appears in EDID.

## 13.3 Resolution changes

When a display mode changes:

- Update logical output geometry.
- Update scale calculations.
- Reposition or constrain windows.
- Update panel and dock layout.
- Update pointer/touch mapping.
- Update mirroring transforms.
- Update damage and buffer dimensions.
- Update audio state only if the underlying device requires it.

Avoid unnecessary compositor restarts.

---

# 14. Compositor and rendering implementation

This is a high-risk part of the change. Inspect the active implementation before touching it.

## 14.1 Multi-output support

Determine whether the compositor supports multiple outputs and how it represents them.

If it does, use the supported output-management path.

If it does not, establish whether the missing support is due to:

- Compositor architecture.
- DRM/KMS driver limitations.
- Framebuffer-only presentation.
- Vendor display controller limitations.
- Missing external connector integration.
- A Nuxel-specific bridge limitation.

Implement only what is technically supported.

If the current architecture fundamentally cannot present to an external output, do not invent a userspace workaround that cannot reach the hardware. Identify the precise required driver/backend work and report it.

## 14.2 Framebuffer bridge

If Nuxel's active framebuffer bridge is involved:

- Inspect its actual source and runtime ownership.
- Determine whether it assumes a single output.
- Determine how buffers are acquired and presented.
- Determine whether the external output can be integrated safely.
- Preserve the single-writer invariant for `/dev/fb0`.
- Do not make a second bridge instance write to the same framebuffer.
- Do not bypass the compositor's ownership model.

If the external display is driven by a separate DRM connector, use that path rather than trying to write a second display into the internal framebuffer.

## 14.3 Buffer lifecycle

Verify:

- Correct buffer allocation.
- Correct format and modifier support.
- Correct dimensions.
- Correct stride.
- Correct lifetime and synchronization.
- Correct release/fence handling where applicable.
- No use-after-free during hotplug.
- No stale buffer presentation after rotation.
- No black frame after mode transitions.
- No excessive copying.

Do not assume all outputs share the same buffer format.

## 14.4 Resource management

Handle external output lifecycle cleanly.

On disconnect:

- Stop external presentation.
- Release output-specific buffers.
- Remove output-specific surfaces.
- Recompute desktop geometry.
- Restore focus.
- Reassign windows safely.
- Remove stale input mappings.
- Release external audio route state.
- Notify the UI.

All cleanup operations must be idempotent.

A repeated disconnect event must not corrupt the compositor or leave an invisible input-blocking surface.

---

# 15. Input, touch and window focus

External output support must not damage existing input behavior.

Test:

- Phone touchscreen while mirroring.
- Phone touchscreen while in separate-desktop mode.
- Phone Back/Home/Tabs navigation.
- External keyboard if available.
- External mouse if available.
- Pointer crossing between outputs if supported.
- Focus switching between phone and external applications.
- Fullscreen app focus.
- External display disconnect while pointer is on that display.
- Touch transformation after rotation.
- Touch transformation after resolution changes.

Ensure that the display manager and compositor agree on the coordinate spaces.

Do not globally remap the phone touchscreen to the external display.

Do not break the existing three-button navigation or gesture zones.

---

# 16. Performance and reliability

Measure rather than guess.

Capture baseline and post-change values where possible:

- CPU load.
- Memory use.
- Compositor frame timing.
- Frame rate.
- Missed frames.
- Display latency.
- Buffer allocation.
- Memory bandwidth indicators, if available.
- Audio underruns.
- Kernel errors.
- Service restarts.

Test the phone UI while HDMI is active.

Test fullscreen video or a representative moving application if supported.

Do not claim a specific FPS unless measured.

Do not sacrifice the internal display's smoothness for external output.

Avoid:

- Polling loops that consume CPU.
- Excessive EDID reads.
- Repeated full-screen copies.
- Repeated compositor restarts.
- Arbitrary fixed sleeps.
- Duplicate notifications.
- Unbounded retries.
- Memory leaks on repeated hotplug.

Use bounded retries and clear failure states.

---

# 17. Automated tests

Add tests using the repository's existing test framework.

Do not invent a parallel test framework.

At minimum, cover:

## 17.1 Connection lifecycle

- Disconnected → connecting.
- Connecting → capabilities detected.
- Capabilities detected → notification pending.
- Notification action → mirroring.
- Notification action → separate desktop.
- Disconnect during negotiation.
- Disconnect during mirroring.
- Disconnect during separate desktop.
- Reconnect after disconnect.
- Duplicate hotplug events.
- Stale asynchronous event rejection.

## 17.2 Notification

- Both mode actions exist.
- Both actions invoke the real display manager.
- Notification is not duplicated.
- Notification reappears after a genuine new connection.
- Dismissal does not change display mode.
- Failed mode activation reports an error.
- Notification remains accessible when initially dismissed.

## 17.3 Mirroring

- Internal display remains enabled.
- External output receives mirrored content.
- Scaling calculations preserve aspect ratio.
- Rotation transform is applied exactly once.
- Mode changes update geometry.
- Disconnect returns to internal-only mode.

## 17.4 Separate desktop

- Independent workspace is created.
- Window placement respects output geometry.
- Fullscreen targets the correct output.
- Pointer and touch mapping use the correct output.
- Phone orientation does not rotate external desktop.
- Disconnect restores windows safely.

## 17.5 HDMI audio

- Audio capability discovery is handled.
- HDMI audio device appearance is handled.
- Output selection works.
- Disconnect triggers safe fallback.
- Reconnect permits HDMI audio selection.
- Missing audio hardware is reported accurately.

## 17.6 Regression tests

Run the relevant existing Nuxel test suites, especially those covering:

- Compositor lifecycle.
- Display geometry.
- Orientation.
- Home and Back.
- Fullscreen.
- Notification handling.
- Touch and pointer input.
- Audio.
- Service startup and shutdown.

---

# 18. Build, deploy and live verification

## 18.1 Build

Build the affected components using the repository's established commands.

Run:

- Formatting and lint checks.
- Type checks, if used.
- Unit tests.
- Integration tests.
- Existing relevant regression suites.
- Build checks.

Do not hide failures by skipping tests without documenting why.

## 18.2 Deployment

Inspect the deployment scripts under `./scripts`.

Choose the smallest safe deployment route.

Before deployment:

- Record the current commit.
- Record modified files.
- Back up affected configuration.
- Preserve the current working system state.
- Confirm that rollback is possible.

Do not reboot unless necessary.

Do not restart the whole graphics stack unless required and justified.

Do not terminate the SSH session intentionally.

After deployment, verify:

- Expected binaries and assets are installed.
- Expected service versions are running.
- Expected configuration is active.
- No old process is still serving stale code.
- No deployment step silently failed.

## 18.3 Physical verification matrix

The final report must include this matrix:

| Test | Required result | Evidence |
|---|---|---|
| HDMI detection | External display detected | Kernel/sysfs/compositor state |
| EDID | Valid capabilities read | EDID diagnostics |
| External picture | Actual image visible | Physical observation |
| Mirroring | Same live phone content visible | Physical observation |
| Separate desktop | Independent workspace visible and usable | Physical observation |
| Phone portrait | Internal orientation correct | Physical observation |
| Phone landscape | Internal orientation correct | Physical observation |
| Mirroring rotation | External mirror follows phone correctly | Physical observation |
| Separate desktop rotation | External desktop remains independent | Physical observation |
| Phone touch | Still works | Physical interaction |
| External input | Works where supported | Physical interaction |
| HDMI audio | Sound heard from external display | Physical listening |
| Phone speaker | Still selectable | Audio test |
| Disconnect | External state cleaned up | Physical disconnect + logs |
| Reconnect notification | Appears again | Physical observation |
| Mirror action | Works after reconnect | Physical observation |
| Separate action | Works after reconnect | Physical observation |
| Regression | Existing Nuxel UI remains usable | Test evidence |

Do not mark any physical test as passed without physical evidence.

If the agent has no means of physically observing the screen or hearing audio, it must state that limitation and leave the relevant test unverified.

---

# 19. Required troubleshooting and persistence

The feature must work beyond one manually configured session.

Inspect how Nuxel starts its display and audio services.

Ensure the solution survives:

- Normal application launches.
- Lock/unlock.
- Display sleep/wake.
- HDMI disconnect/reconnect.
- Compositor lifecycle events.
- Nuxel service restarts.
- Phone reboot, where safe and testable.

Do not persist a transient HDMI connector state as if the cable were permanently connected.

Persist user preferences, not stale hardware state.

On boot, detect the actual connected outputs and reconstruct the display state from current hardware.

Do not leave the system in an invalid separate-desktop state if the monitor is absent.

---

# 20. Documentation

Update the appropriate Nuxel documentation.

Document:

- Supported USB-C HDMI hardware path.
- How connection detection works.
- Mirror mode.
- Separate desktop mode.
- Orientation behavior.
- HDMI audio behavior.
- Supported resolutions and refresh rates.
- Known hardware limitations.
- How to inspect display state.
- How to troubleshoot failed connection or audio.
- Relevant logs and diagnostics.
- How to restore internal-only mode.

Do not document features as supported if they were not verified.

---

# 21. Final report: REPORT-PWNAGE-99000.md

Create `REPORT-PWNAGE-99000.md` in the repository.

Include:

## A. Executive summary

- Initial HDMI state.
- Root cause.
- Changes made.
- Current live state.
- Whether mirroring works.
- Whether separate desktop works.
- Whether orientation works.
- Whether HDMI audio works.
- Whether reconnection notification works.

## B. Initial diagnosis

- Device identity.
- Kernel and OS version.
- Type-C/DP Alt Mode findings.
- HPD findings.
- EDID findings.
- DRM/KMS/compositor findings.
- Audio findings.
- Relevant logs.

## C. Implementation

List every changed file and explain:

- What it does.
- Why it was changed.
- Which failure it fixes.
- How it interacts with existing Nuxel components.

## D. Test evidence

Include:

- Commands executed.
- Automated test results.
- Build results.
- Runtime state.
- Physical observations.
- Audio verification method.
- Reconnection test evidence.

Separate automated results from physical results.

## E. Limitations

List every remaining blocker, including hardware or driver limitations.

For each blocker include:

- Exact failure point.
- Evidence.
- What was attempted.
- What remains necessary.
- Whether it requires kernel, driver, device-tree, firmware, adapter, or userspace work.

## F. Deployment and rollback

Record:

- Commit.
- Build artifact/version.
- Deployment script used.
- Files/services updated.
- Backup location.
- Rollback procedure.
- Current deployed version.

## G. Final status

Use one of:

- `FULLY_VERIFIED`
- `IMPLEMENTED_BUT_PHYSICAL_VERIFICATION_BLOCKED`
- `PARTIALLY_IMPLEMENTED`
- `BLOCKED_BY_HARDWARE_OR_DRIVER`
- `NOT_COMPLETED`

Only use `FULLY_VERIFIED` if every mandatory acceptance criterion—including actual separate-desktop operation, mirroring, orientation, HDMI audio, and physical disconnect/reconnect notification—has passed.

---

# 22. Acceptance criteria

The task is complete only when all of the following are true:

- [ ] The existing USB-C HDMI hardware connection has been investigated.
- [ ] The actual root cause of the original failure has been identified.
- [ ] HDMI output works on the connected S10+.
- [ ] Mirroring works and shows live content.
- [ ] Separate-desktop mode works as an independent workspace.
- [ ] Both modes can be selected from Nuxel's connection notification.
- [ ] The notification appears on a new HDMI connection.
- [ ] The notification appears again after a physical disconnect/reconnect.
- [ ] The internal phone display remains functional.
- [ ] Phone orientation is respected.
- [ ] External orientation is independent in separate-desktop mode.
- [ ] Mirroring orientation is correct.
- [ ] Resolution, scaling, and aspect ratio are correct.
- [ ] Touch and pointer input remain correct.
- [ ] HDMI audio is exposed and selectable where supported.
- [ ] Actual sound is physically heard through the external display.
- [ ] Audio falls back safely after disconnect.
- [ ] External surfaces and buffers are cleaned up.
- [ ] Repeated hotplug does not create duplicate outputs or notifications.
- [ ] Automated tests pass.
- [ ] Relevant regression tests pass.
- [ ] The fix is deployed to the actual device.
- [ ] The final report contains evidence and accurate limitations.

**Do not call the task finished because a build passes or a display connector appears. The target is a working external display experience on the actual phone.**

---

# 23. Final instruction to the agent

Start by inspecting the currently connected HDMI hardware and the active Nuxel display/audio architecture.

Keep the existing connection intact while investigating.

Follow the real signal path from USB-C negotiation through display presentation and audio routing. Fix the actual failure rather than building a superficial UI around it.

Implement both display modes, orientation-aware layout, the reconnect notification, and HDMI audio as one integrated feature.

Use the existing deployment workflow in `./scripts`, preserve SSH access and rollback, deploy the solution, and continue testing until the second display is demonstrably working.

**The final success condition is not “HDMI detected.” It is: the user plugs in HDMI, Nuxel asks whether to mirror or use a separate desktop, either choice works, orientation is correct, and audio plays through HDMI.**
