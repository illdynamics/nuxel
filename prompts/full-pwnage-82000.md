# FULL PWNAGE-82000 — Nuxel Mobile OS Completion and Performance Optimization
## Audio recovery, sound manager, Doom twin-D-pad controls, software transaction feedback, GPU/compositor tuning, GTK/Flatpak performance, hardware meters, yt-dlp, Notes, Calendar, widgets, desktop icon movement, Recorder, appearance, Software keyboard and Vesktop

**Project:** Nuxel — Mobile Linux for Control Freaks  
**Target device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**SoC:** Exynos 9820  
**GPU:** Mali-G76 MC12  
**OS:** Fedora-based Nuxel ARM64  
**Desktop:** Phoc/Wayland with custom Nuxel shell  
**Deployment:** Wi-Fi SSH, root console  
**SSH key:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Priority:** Critical  
**Starting state:** Phone booted normally into Nuxel  
**TWRP:** Not required  
**Kernel reflash:** Not expected  
**Primary objective:** Restore sound, finish desktop application functionality, complete media/integration tasks, implement the new Doom and Software improvements, and carry out another measured performance optimization round.

---

# 0. Executive mission

Complete the Nuxel mobile desktop and application ecosystem work described in this document.

This is a comprehensive implementation task, not a set of UI mockups.

The following subsystems must work together:

- Core audio output and capture.
- Nuxel sound library.
- Clock alarms and timers.
- Volume feedback.
- Desktop dock.
- DevMgmt graphics diagnostics.
- GTK and Flatpak application startup.
- GPU memory metrics.
- Media Downloader.
- Notes.
- Calendar.
- Keyboard/input method.
- Widgets.
- Desktop/workspace management.
- Draggable application icons.
- Doom mobile controls.
- Recorder.
- Software application management.
- Appearance settings.
- Vesktop.
- GPU/compositor performance.

There are three newly emphasized requirements:

1. **Doom:** left movement D-pad and right aiming D-pad, matching in size and vertical alignment, with a fire button beneath each. Only Map remains from the old auxiliary control group, and Map must work.
2. **Software:** installation and removal must show actual progress and an explicit completed/failed result, not merely text saying installing/removing or a checkbox changing.
3. **Performance:** conduct a further evidence-based performance tuning round focused on Mali, Phoc, Wayland, WebKit and the framebuffer bridge. Remove unnecessarily fancy effects and optimize assets without degrading image quality.

Do not compromise stability for theoretical benchmarks.

---

# 1. Mandatory remote access and deployment setup

Start with the phone booted normally into Nuxel.

Do not start in TWRP.

Do not flash the kernel.

The task is expected to be completed through the established Wi-Fi SSH/root console workflow.

## 1.1 SSH key

Use:

```text
~wicked/.ssh/wicked_wqn_id_rsa
```

Verify that it is readable.

Do not generate another key.

Do not copy or reveal the private key.

## 1.2 Find the current Wi-Fi address

Discover the actual active host using:

- Existing SSH configuration.
- Existing known_hosts.
- Nuxel debug tools.
- Current device network state.
- The established live SSH helper.

Known helper:

```text
scripts/s10plus-debug-pack/nuxel-live-ssh.sh
```

Inspect its supported syntax.

Example status/discovery command:

```bash
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
    --transport wlan \
    --status
```

Do not use a stale IP or invent a host.

## 1.3 Connect

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
    -o IdentitiesOnly=yes \
    -o BatchMode=yes \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=15 \
    root@<DISCOVERED_NUXEL_WIFI_HOST>
```

Preserve SSH host-key checking.

If the host key changed, verify the device identity and fingerprint.

Do not disable host-key validation.

Verify root:

```bash
id
whoami
hostname
uname -a
```

Maintain access throughout the work.

Do not restart networking, Wi-Fi or SSH without a verified need and rollback route.

---

# 2. Repository and runtime audit

Identify the real current source of truth.

Inspect:

- Repository branch.
- Commit.
- Working tree.
- Untracked files.
- Build outputs.
- Current device image.
- Runtime services.
- Application processes.
- Configuration.
- Installed assets.
- Data directories.

Useful areas include:

```text
pwa/nuxel-home/
pwa/nuxel-apps/
services/nuxel-bridge/
services/
configs/nuxel/
tools/s10plus/
images/s10plus/
assets/
```

Search the actual repository for:

- Clock.
- Sound.
- Audio.
- Media Downloader.
- yt-dlp.
- Notes.
- Calendar.
- Recorder.
- Software.
- NuXtore.
- Doom.
- Vesktop.
- DevMgmt.
- Hardware meters.
- Widgets.
- Desktop.
- Launcher.
- Dock.
- Appearance.
- GPU.
- EGL.
- Mali.
- Phoc.
- wlroots.
- `nuxel-wl-fb`.

For every modification, identify:

- Source file.
- Active build target.
- Installed destination.
- Runtime owner.
- Systemd unit.
- Configuration.
- Bridge/API.
- User data.

Do not patch stale source files.

Do not claim success if the active device does not execute the updated code.

## 2.1 Preserve user state

Before changing anything:

- Preserve existing sounds.
- Preserve recordings.
- Preserve Notes.
- Preserve Calendar events.
- Preserve downloaded media.
- Preserve widget configuration.
- Preserve desktop count.
- Preserve icon positions.
- Preserve Home settings.
- Preserve current package installations.
- Preserve user appearance settings.
- Preserve existing Nuxel data.

Use reversible changes and a tracked branch.

---

# 3. Priority and dependency order

Perform the work in stages.

### Stage 1 — Restore audio

Sound currently appears broken globally.

Prove actual output and input before implementing more sound features.

### Stage 2 — Central sound manager and assets

Move the repository sound collection, install user sounds, implement settings and preview.

### Stage 3 — Clock and volume feedback

Use the working shared sound manager.

### Stage 4 — Dock and DevMgmt

Fix flicker, graphics capability display and overlapping tabs.

### Stage 5 — GPU memory metrics and app startup

Implement truthful GPU memory metrics and measure GTK/Flatpak performance.

### Stage 6 — Media Downloader

Complete yt-dlp, cookies, MP3/MP4, progress and media indexing.

### Stage 7 — Notes and Calendar

Implement persistence, event CRUD and cross-application integration.

### Stage 8 — Widgets and desktop

Add widgets, desktop management and draggable icons.

### Stage 9 — Doom controls

Implement twin D-pads, duplicated fire controls and a functional Map button.

### Stage 10 — Recorder and Software

Fix microphone/waveform and Software app keyboard/transaction state.

### Stage 11 — Vesktop

Verify native ARM64 packaging and owner-assisted login.

### Stage 12 — Performance round and deep audit

Tune the system based on measurements, then run full regression.

Do not spend time on polish while a fundamental dependency is broken.

---

# 4. Core audio system — root-cause diagnosis and recovery

This is the highest priority.

The owner reports:

- Clock alarm sound does not play.
- Clock timer sound does not play.
- Volume-change sound no longer plays.
- General sound appears to have stopped working.
- Recorder produces a glitched sound when opened.
- Recorder reports microphone available but does not yet provide a proper waveform.

These symptoms may share one audio backend or session problem.

## 4.1 Identify the actual backend

Inspect the physical phone.

Determine whether Nuxel currently uses:

- ALSA.
- PipeWire.
- WirePlumber.
- PulseAudio compatibility.
- Direct ALSA playback.
- GStreamer.
- Another custom audio service.

Do not assume the installed backend.

Inspect:

- Services.
- Devices.
- Default sink.
- Default source.
- Mixer state.
- Device routing.
- Permissions.
- User/system audio sessions.
- Audio sockets.
- Codec/decoder availability.
- Current audio-related environment variables.
- Kernel audio logs.

Do not install a competing sound server.

## 4.2 Playback diagnosis

Test using the current system stack.

Use a known-good WAV and MP3.

Test:

1. Playback device enumeration.
2. Playback pipeline creation.
3. First sample delivery.
4. Actual physical speaker output.
5. Headphone route where supported.
6. Playback shutdown.
7. Repeated playback.
8. Playback while changing volume.

Check mute, gain, route and decoder.

Record exact errors.

A successful pipeline setup does not prove sound is audible.

## 4.3 Capture diagnosis

Test microphone separately.

Verify:

- Hardware device exists.
- Capture route.
- Permissions.
- Sample rate.
- Format.
- Channels.
- Input level.
- Real PCM samples.
- Output recording file.
- Playback of the file.

The UI claim `microphone available` is not enough.

## 4.4 Root-cause report

Determine why sound stopped.

Possible causes:

- Audio service down.
- Session service disconnected.
- Default device changed.
- Speaker muted.
- ALSA mixer wrong.
- PipeWire routing failure.
- Device suspended.
- Wrong application user/session.
- Decoder missing.
- Asset lookup failure.
- Sound service code regression.
- Audio focus conflict.
- Startup sequencing.

Fix the actual cause.

Do not hide it by simply restarting audio services in a loop.

---

# 5. Sound assets and `~/Sounds`

## 5.1 Required repository layout

The complete sound collection must live in:

```text
./assets/nuxel-sounds/
```

The original repository folder:

```text
./nuxel-sounds/
```

must be moved into the assets directory.

Move the existing:

```text
nuxel-pow.mp3
nuxel-alarm.mp3
```

into that collection before completing the move.

Preserve all supplied sound files.

Do not leave contradictory copies in multiple source directories.

## 5.2 Device installation

Copy/install every supplied sound into:

```text
~/Sounds/
```

Preserve any user-custom files already there.

Use correct user ownership and permissions.

Do not overwrite changed files without backing them up.

## 5.3 Central sound library

Create one central index of sounds.

For every sound record:

- Stable ID.
- File path.
- Display name.
- Format.
- Duration.
- Sample rate.
- Channels.
- File size.
- Bundled/custom source.
- Decoder availability.

Automatically discover additions and updates.

Use a watcher or controlled refresh mechanism.

Do not rescan the entire library every time a UI component renders.

---

# 6. Central sound manager and Settings

Implement a single playback and event-assignment service.

It must provide:

- Asset lookup.
- User selection.
- Preview.
- Playback.
- Stop/cancel.
- Event routing.
- Volume.
- Audio output.
- Decoder.
- Persistent assignment.
- Runtime reload.
- Error reporting.

Do not implement a separate sound player inside Clock and another inside Home.

## 6.1 Sound assignment choices

Add a Sounds section in Settings.

Provide separate selections for:

| Event | Default |
|---|---|
| Volume change | `nuxel-pow.mp3` |
| Boot-up | `nuxel-pow.mp3` |
| Alarm | `nuxel-alarm.mp3` |
| Timer | `nuxel-alarm.mp3` |
| New messages | User-selected |
| Notifications | User-selected |
| Future events | Extensible |

The actual selection must be saved in central Settings.

## 6.2 Per-event UI

Each event must have:

- Event label.
- Current sound.
- Preview.
- Browse.
- Reset.
- Persistent selection.
- Missing-file status.

## 6.3 Automatic detection

New MP3s should appear automatically.

Support additional formats only when the installed Nuxel backend can decode them.

When a file is renamed or deleted, update the index.

If an assigned file disappears, show an explicit warning and use a safe fallback.

## 6.4 Browse

Every assignment needs its own Browse button.

Use the system file picker.

Permit selecting a custom file from the filesystem.

Validate the selected file.

Offer a stable copy into `~/Sounds/Custom/` or preserve a persistent user-selected path.

Do not reference temporary file-picker paths.

Preview the sound before confirming.

---

# 7. Clock alarm and timer

Fix both alarm and timer playback.

Default asset:

```text
~/Sounds/nuxel-alarm.mp3
```

Use the central sound manager.

Do not resolve the file using relative `./assets` paths.

## 7.1 Background scheduling

The alarm must not depend on the Clock UI remaining open.

Inspect the existing scheduler and service design.

Use one authoritative alarm/timer backend.

Persist scheduled state.

Prevent duplicate triggers.

Support:

- Alarm.
- Timer.
- Dismiss.
- Stop playback.
- Snooze where supported.
- Restart recovery.
- Reboot semantics.

## 7.2 Testing

Test with Clock:

- Foreground.
- Background.
- Closed.
- Reopened.
- Multiple alarms.
- Active timer.
- Timer completion.
- Dismissal.

Verify actual speaker output.

Do not mark complete based only on an application callback.

---

# 8. Volume sound

Restore volume-change feedback.

Default:

```text
nuxel-pow.mp3
```

The user previously experienced a 2–3 second delay; the current symptom is total silence.

Diagnose both.

Instrument:

1. Volume input.
2. Volume backend update.
3. Event dispatch.
4. Sound-manager receipt.
5. Decoder.
6. Audio output.
7. First audible frame.

Use a preloaded sound buffer or persistent low-latency playback route.

Do not initialize a new sound process for every change.

Do not block the volume slider.

Do not queue dozens of stale sound events.

Target approximately 100 ms or less from input to audible output in normal conditions.

The selected sound must be adjustable immediately through Settings.

---

# 9. Dock flickering

Fix the four bottom desktop dock apps intermittently flickering.

They must remain pinned.

Inspect:

- App state updates.
- Component recreation.
- CSS animation.
- DOM identity.
- Image/icon loading.
- Duplicate renderers.
- Z-order.
- Layer-shell ownership.
- Home/app transitions.
- Resize observers.
- Orientation changes.
- App discovery refresh.
- Surface redraw.

Use stable application keys.

Avoid rebuilding the entire dock on every state update.

Test:

- Home.
- App drawer.
- App launch.
- App close.
- Widget placement.
- Desktop switching.
- Rotation.
- Lock/unlock.
- Launcher reload.

---

# 10. DevMgmt graphics acceleration and tab layout

## 10.1 Graphics status

Add a detailed graphics acceleration section.

The known Nuxel display/graphics path includes:

```text
Phoc / Wayland
      |
      v
zwlr_screencopy
      |
      v
nuxel-wl-fb
      |
      v
/dev/fb0
      |
      v
Samsung DECON / AMOLED
```

The S10+ uses Mali-G76 MC12 with Mali kbase.

Probe the live system.

Report:

- Driver.
- Device.
- EGL.
- GLES.
- Phoc renderer.
- WebKit renderer.
- WebKit transport.
- DRM nodes.
- VGEM.
- GBM.
- DMA-BUF.
- Formats/modifiers.
- Phoc import.
- Framebuffer bridge.
- Physical output.
- CPU copy/scale.

## 10.2 Acceleration status

Do not collapse all stages into one GPU badge.

Support:

- GPU RENDERING.
- GPU-RENDERED / SHM-PRESENTED.
- GPU-RENDERED / DMA-BUF-PRESENTED.
- FULLY ACCELERATED.

Expose:

- PASS.
- PARTIAL.
- UNAVAILABLE.
- DEGRADED.
- NOT TESTED.

Do not mark fully accelerated while a CPU copy remains in the final presentation path.

Do not claim zero-copy if not demonstrated.

## 10.3 Tab text overlap

Fix DevMgmt tabs.

Inspect:

- Width.
- Flex/grid sizing.
- Font scale.
- Text wrapping.
- Text baseline.
- Padding.
- Icon alignment.
- Overflow.
- Landscape breakpoint.

Test both orientations.

Do not merely shrink text until it fits.

---

# 11. GPU memory meter and Home Settings

Show GPU memory as amount and percentage by default, where the data supports a valid percentage.

Example:

```text
GPU Memory: 84 MB (12%)
```

This is illustrative only.

The S10+ Mali GPU uses shared system memory.

Do not represent it as a conventional discrete VRAM device.

Identify actual available metrics:

- Kbase per-context allocations.
- Total GPU allocations.
- GPU page count.
- Driver-reported memory usage.
- Valid memory budget, if exposed.

Only calculate percentage when numerator and denominator describe the same supported metric.

Do not use total system RAM as a fabricated dedicated VRAM capacity.

If no reliable denominator exists, show amount and mark percentage unavailable.

## 11.1 Home Settings

Add:

- Amount + percentage (default).
- Percentage only.
- Amount only.

Persist setting.

Update live display.

Keep portrait and landscape layout correct.

---

# 12. GTK and Flatpak startup performance

Profile startup rather than guessing.

Measure:

- Launcher.
- Process spawn.
- D-Bus.
- Portal.
- Bubblewrap.
- User namespaces.
- Runtime setup.
- Dynamic linker.
- GTK/libadwaita.
- Fontconfig.
- Icon/theme.
- Wayland.
- First frame.

Test native and Flatpak apps separately.

Investigate:

- Blocking app discovery.
- Duplicate desktop-file parsing.
- Icon cache.
- Fontconfig cache.
- D-Bus activation.
- Portal activation.
- Runtime mounting.
- CPU pressure.
- Memory.
- Filesystem latency.
- Repeated process startup.

Fix only proven bottlenecks.

Do not disable Flatpak sandboxing.

Do not leave every app permanently running.

---

# 13. Media Downloader — yt-dlp

Use yt-dlp as the actual download engine.

Official documentation:

- https://github.com/yt-dlp/yt-dlp
- https://github.com/yt-dlp/yt-dlp/wiki/FAQ

## 13.1 URL processing

When user pastes a URL:

1. Validate.
2. Retrieve metadata.
3. Display title.
4. Display thumbnail.
5. Display duration.
6. Display source.
7. Choose MP3 or MP4.
8. Choose cookie source.
9. Download.
10. Display progress.
11. Support cancellation.
12. Save output.
13. Refresh Gallery.

Use safe argument arrays.

Never concatenate user input into a shell command.

## 13.2 MP3

Use supported preset:

```bash
yt-dlp -t mp3 "<URL>"
```

Verify FFmpeg and FFprobe.

## 13.3 MP4

Use supported preset:

```bash
yt-dlp -t mp4 "<URL>"
```

Verify installed version and actual codec/remux behavior.

Show when re-encoding is required.

## 13.4 Cookie selector

Provide:

- Chrome.
- Firefox.
- Nuxel.
- None.

Chrome and Firefox should use native `--cookies-from-browser` where available.

Nuxel is not a built-in yt-dlp browser identifier.

If Nuxel uses WebKitGTK, investigate its actual cookie manager and create a secure export adapter to Netscape-format cookie data if supported.

Pass temporary cookie files with `--cookies`.

Use:

- Private temporary directory.
- Restrictive permissions.
- No cookie logging.
- Cleanup after success/failure.
- User consent.

If no safe Nuxel cookie adapter can be implemented, mark the option unavailable. Do not fake compatibility.

Respect website terms and do not bypass DRM/paywalls/access controls.

## 13.5 Download destination

Use Nuxel Downloads.

Show:

- Progress.
- Speed.
- ETA.
- Destination.
- Cancel.
- Retry.
- Open in Gallery.
- Delete.

Ensure all associated subprocesses terminate on cancellation.

---

# 14. Notes

Save all notes under:

```text
~/Notes/
```

Use a documented, durable format.

Implement:

- Create.
- Edit.
- Autosave.
- Explicit save.
- Rename.
- Delete.
- Search.
- Sort.
- Preview.
- Recovery.
- Persistence.

Use atomic writes and preserve existing notes.

Provide a Gallery-style grid/list preview.

Add actions to convert a note into:

- Alarm.
- Calendar event.
- Reminder.

Extract date/time suggestions but require confirmation before creating an event.

Use the shared Calendar/Clock services.

Do not create incompatible data stores.

---

# 15. Calendar

Calendar currently cannot create events.

Fix the actual event backend and UI.

## 15.1 Diagnose

Inspect:

- UI callbacks.
- Bridge/API.
- Schema.
- Persistent storage.
- Date/time parsing.
- Permissions.
- Calendar scheduler.
- Reminder service.
- UI refresh.

Find why save operations fail.

## 15.2 Full event functionality

Implement:

- Create.
- View.
- Edit.
- Delete.
- All-day.
- Title.
- Description.
- Start/end date.
- Start/end time.
- Location.
- Reminders.
- Timezone.
- Persistence.

Verify actual disk persistence and reloading.

## 15.3 Time validation

Validate:

- End after start.
- Timezone.
- Daylight-saving transitions.
- Missing required values.
- Date format.
- Time format.
- Duplicate event submission.

## 15.4 Calendar keyboard

The unwanted dark-blue keyboard currently appears alongside the correct Nuxel keyboard.

Identify and remove the obsolete implementation from the active code path.

Use the same grey/blue/black/white keyboard used by Clock's hour fields.

For time entry:

- Numeric/time layout.
- Digits.
- Separator.
- Backspace.
- Confirm.
- Proper focus.

Only one keyboard may exist.

Back closes keyboard first.

Swipe down closes keyboard.

Do not create a Calendar-specific duplicate.

---

# 16. Widgets and desktop management

Widgets currently do not appear.

Implement the real widget system.

## 16.1 Desktop long-press

Long-press an empty desktop background opens a context menu:

- Home Settings.
- Widgets.

Do not immediately open Home Settings.

Do not show the background menu when dragging an existing icon.

## 16.2 Widget registry

Each widget includes:

- Stable ID.
- Name.
- Description.
- Preview.
- Icon.
- Supported sizes.
- Data provider.
- Renderer.
- Settings.
- Refresh policy.
- Permissions/dependencies.

Only advertise functional widgets.

## 16.3 Widget picker

The user must be able to:

- Open Widgets.
- Browse available widgets.
- Select one.
- Choose desktop.
- Place it.
- Resize it where supported.
- Configure it.
- Remove it.

Placement must immediately appear on the chosen desktop.

Persist positions and configuration.

## 16.4 Desktops

The system currently has two desktops.

Preserve them and their content.

Add Home Settings controls:

- Add desktop.
- Remove desktop.
- Rename where supported.
- Reorder.
- Select default.
- Select active desktop.
- Configure count.

When deleting a desktop, ask where its content should go.

Do not erase icons or widgets.

---

# 17. Movable desktop application icons

The owner can currently add, resize and delete icons but cannot move them.

Implement persistent drag-and-drop.

## 17.1 Drag initiation

A deliberate long-press on an app icon enters drag mode.

Show:

- Selected state.
- Drag ghost.
- Preview location.
- Valid/invalid drop target.

Do not start dragging on an ordinary quick tap.

## 17.2 Grid snapping

Icons must snap to the existing configured grid.

Prevent:

- Overlap.
- Invalid placement.
- Off-screen positioning.
- Widget collisions.
- Dock/navigation collision.

Persist actual coordinates/grid positions.

## 17.3 Cross-desktop drag

When dragging to a desktop edge:

- Left edge, held approximately one second: previous desktop.
- Right edge, held approximately one second: next desktop.

The icon remains held throughout the transition.

The user can drop it onto the new desktop.

Use edge dwell and hysteresis.

Do not rapidly switch multiple desktops while the finger remains at an edge.

## 17.4 Gesture conflicts

Keep distinct:

- Background long-press.
- Icon drag.
- Icon tap.
- Resize.
- Delete.
- Desktop swipe.

Handle pointer/touch cancellation safely.

---

# 18. Desktop dock flicker

Fix the four bottom dock apps flickering sometimes.

Keep the four pinned applications.

Inspect:

- Component identity.
- DOM keys.
- Layer-shell.
- Animation.
- App discovery.
- Process tracking.
- Icon loading.
- Duplicate event listeners.
- Layout refresh.
- Framebuffer damage.
- Output changes.

Use stable keys and update only affected icon states.

Do not rebuild the dock on every app lifecycle event.

Test repeated app opening/closing, desktop switching, app drawer, lock/unlock and rotation.

---

# 19. Doom — twin D-pads and two fire buttons

Redesign the Doom mobile controls.

The desired layout uses both thumbs symmetrically.

## 19.1 Final layout

```text
+-----------------------------------------------+
|                                               |
|                 DOOM GAME                     |
|                                               |
|                                               |
|                                               |
|    LEFT D-PAD                 RIGHT D-PAD     |
|       WALK                       AIM          |
|                                               |
|     [  UP  ]                   [  UP  ]       |
|     [L D-PAD]                  [R D-PAD]      |
|                                               |
|      [FIRE]                     [FIRE]        |
|                                               |
|                                     [ MAP ]   |
+-----------------------------------------------+
```

Actual visual styling should match Nuxel's Doom interface.

The two D-pads must have identical dimensions and align at the exact same vertical height.

The Fire buttons must be identical and positioned directly below each respective D-pad.

## 19.2 Left D-pad — movement

The left D-pad controls player movement only.

Required:

- Up.
- Down.
- Left.
- Right.
- Diagonal movement where supported.
- Continuous movement while held.
- Reliable touch release.
- No stuck movement after interruption.

## 19.3 Right D-pad — aiming

The right D-pad controls look/aim only.

Required:

- Horizontal look.
- Vertical look if supported by the engine/configuration.
- Sensitivity.
- Dead zone.
- Response curve where appropriate.
- Smooth continuous aim while held.
- Correct touch release.

Do not accidentally move the player while using the right aim control.

Do not rotate the phone display through the right D-pad.

If the selected Doom engine uses a different internal look/mouselook input model, adapt through its supported input interface.

Do not fake right-side aiming by reusing movement commands.

## 19.4 Two identical Fire buttons

Place one Fire button below each D-pad.

Both buttons must:

- Have identical dimensions.
- Have identical hit targets.
- Trigger exactly the same game fire action.
- Work independently.
- Work with simultaneous movement/aim input.
- Support press-and-hold firing if appropriate.

Test firing using the left thumb and right thumb separately.

Test holding movement and firing simultaneously.

Test aiming and firing simultaneously.

Do not allow one button to steal or cancel another pointer's active touch.

## 19.5 Remove old controls

Inspect existing HUD and control definitions.

Remove:

- Old separate Left button.
- Old separate Right button.
- The other obsolete auxiliary button(s).

Preserve:

- Map button.
- Newly added left Fire.
- Newly added right Fire.
- Essential pause/menu/gameplay controls if they are outside the specified obsolete group.

Do not accidentally remove the new Fire buttons.

The Map button must be the only remaining button from the old auxiliary control group.

## 19.6 Map functionality

Map must open the actual Doom automap.

Verify:

- Correct map overlay/state.
- Actual game map.
- Zoom/scroll if provided by engine.
- Input mapping.
- Map close/back.
- Gameplay resumes.
- No stale touch grabs.

Do not make a button that only changes color without invoking the map.

## 19.7 Layout in all orientations

The HUD must remain proportionally correct in the supported game orientations.

D-pads remain equal and aligned.

Fire buttons remain underneath.

Keep all controls inside safe areas.

Do not overlap critical game information.

## 19.8 WAD/engine packaging

Keep Nuxel Doom completely installable via NuXtore.

Chocolate Doom may remain an internal engine dependency if required, but the user should not have to separately discover and install a visible Chocolate Doom application.

Remove duplicate standalone Chocolate Doom UI/package only if no other app needs it.

Bundle only legally distributable WAD files.

Provide a user import workflow for legally obtained commercial WADs.

Verify a fresh install from a clean device/app state.

Preserve original Doom graphics.

---

# 20. Recorder — microphone and waveform

The Recorder currently reports microphone availability but produces a glitched startup sound and no waveform.

Fix the actual audio capture path.

## 20.1 Inspect capture

Check:

- Microphone device.
- Capture backend.
- ALSA/PipeWire/PulseAudio route.
- Permissions.
- Sample rate.
- Sample format.
- Channels.
- Input gain.
- Buffering.
- Capture stream state.
- Playback monitoring.
- Device warm-up.

Record actual samples.

## 20.2 Opening glitch

Reproduce and capture logs.

Identify whether the glitch is caused by:

- Stream initialization.
- Wrong sample format.
- Uninitialized buffer.
- Playback monitor.
- Abrupt output gain.
- Capture/output collision.
- Buffer underrun.
- Duplicate audio route.

Do not mute the entire recorder to hide it.

## 20.3 Waveform

Generate the waveform from real microphone PCM.

Use downsampled peak/RMS buckets.

Display:

- Live waveform during recording where practical.
- Completed waveform.
- Duration.
- Playback position.
- Play/pause.
- Seek if supported.
- Recording state.

Long recordings must not create huge per-sample UI structures.

Waveform failures must not destroy the recording.

## 20.4 Save/playback

Save recordings in a stable user location.

Preserve them across application close and reboot.

Refresh Gallery.

Verify actual playback.

---

# 21. Software app — keyboard and transaction feedback

Two separate issues must be fixed.

## 21.1 Keyboard

Software currently opens with the keyboard and the user cannot reliably reveal the triple navigation buttons or dismiss keyboard.

Implement:

- Swipe up to reveal Back/Home/Tabs.
- Swipe down to dismiss keyboard.
- Back dismisses keyboard first.
- Correct navigation remains available.
- No duplicate keyboards.
- Focus clears when leaving the app.

Use the shared keyboard coordinator.

Do not implement another Software-only keyboard.

## 21.2 Installation/removal completion status

The Software app currently says things like:

```text
Installing...
Removing...
```

but does not clearly report completion.

A checkbox appearing/disappearing is insufficient.

Implement explicit transaction state:

```text
idle
queued
resolving
downloading
installing
verifying
completed
removing
removed
failed
cancelled
```

Every operation must have a unique transaction ID.

Show:

- App name.
- Operation.
- Current state.
- Progress where available.
- Completion state.
- Error details.
- Retry where safe.

On successful install:

1. Backend reports completion.
2. Verify actual installed package/ref.
3. Refresh app registry.
4. Refresh launcher.
5. Show a clear `Installed` success message.
6. Enable Launch.

On successful removal:

1. Backend reports completion.
2. Verify app is absent.
3. Refresh app registry.
4. Remove stale launcher entry.
5. Show clear `Removed` confirmation.

On failure:

- Keep actual state.
- Show error.
- Do not claim completion.
- Offer safe retry.

Do not rely on a checkbox as the only status.

Do not report success because the request merely started.

Do not block the Software UI while an operation runs.

Do not allow multiple concurrent conflicting operations for the same ref.

---

# 22. Appearance Settings

Add or retain:

- System default.
- Light.
- Dark.
- Adwaita Dark where supported.

Use supported GTK/libadwaita color-scheme configuration.

Ensure compatibility with native GTK and Flatpak themes.

Do not blindly force `GTK_THEME` globally.

Verify actual installed theme extensions and runtime compatibility.

Do not claim every Qt/Electron/custom app follows GTK appearance settings.

Settings must persist and apply without restarting Phoc.

---

# 23. Vesktop ARM64 integration

Inspect the actual installed Vesktop package.

Verify it is AArch64.

Use the current official release/package if compatible with Nuxel.

References:

- https://github.com/Vencord/Vesktop/releases
- https://vesktop.dev/install/linux/

Inspect:

- Architecture.
- Dependencies.
- Electron/Chromium version.
- Wayland/XWayland.
- GPU.
- Audio.
- Notifications.
- Scaling.
- App data.
- Desktop entry.
- Sandbox.

Prefer the native ARM64 Fedora-compatible package where suitable.

Do not use an x86_64 package.

The owner must enter credentials and complete login/MFA/QR steps interactively.

Never store the user's password in scripts or logs.

Never extract authentication tokens or message data for diagnostics.

---

# 24. Performance optimization round — measure, tune and preserve quality

A separate measured performance optimization round is mandatory.

The goal is smoother interaction, better frame pacing and faster app responsiveness.

Do not blindly apply GPU flags or kernel options.

Do not destabilize working Mali rendering.

## 24.1 Baseline collection

Before performance changes, measure:

- Desktop frame pacing.
- Frame intervals.
- Dropped frames.
- Jank.
- Touch-to-response latency.
- Scroll smoothness.
- Dock update smoothness.
- App drawer opening.
- Launcher reload.
- App startup.
- CPU load.
- GPU load where available.
- Memory pressure.
- Memory bandwidth indicators where available.
- Framebuffer copy/scale duration.
- Audio latency.
- Thermal behavior.

Use reproducible tests.

Record:

- p50.
- p95.
- p99 where meaningful.
- Maximum latency.
- Test duration.
- Device temperature/power state where available.

Avoid comparing a cold test against a warm test.

## 24.2 Identify actual installed versions

Identify exact:

- Phoc version.
- wlroots version/commit.
- Mesa/Gallium version.
- EGL vendor.
- GLES version.
- Mali kbase version.
- WebKitGTK version.
- GTK version.
- Framebuffer bridge build.
- Display mode and geometry.

Do not apply current upstream options to an older Phoc/wlroots build without verification.

Phoc is based on wlroots and provides renderer/environment controls, but exact options vary by installed version.

References for investigation:

- Phoc manual and options: https://manpages.debian.org/testing/phoc/phoc.1.en.html
- Phoc development documentation: https://world.pages.gitlab.gnome.org/phosh/phoc/gettingstarted.html
- wlroots environment variables: https://gitlab.freedesktop.org/wlroots/wlroots/-/blob/master/docs/env_vars.md

The installed source and binary help output are authoritative.

## 24.3 Mali/GPU performance

Preserve the existing working Mali kbase renderer.

Check:

- GPU device access.
- EGL initialization.
- GPU work submission.
- GPU reset/errors.
- Context count.
- Software fallback.
- Buffer allocation.
- DMA-BUF usage.
- Modifier support.
- GPU memory allocation.
- Power/thermal limits.

Do not use software rendering as a performance optimization.

Do not select `pixman` or software renderer just because a test looks simpler.

Do not force an unsupported renderer.

Do not symlink Mali device nodes to fake DRM nodes.

Do not invent VRAM metrics.

## 24.4 Phoc/wlroots tuning

Inspect the actual Phoc config and startup environment.

Only apply options supported by the installed Phoc/wlroots version.

Measure before and after every meaningful setting change.

Investigate:

- Damage tracking.
- Buffer formats.
- Buffer modifiers.
- Render buffer allocation.
- Output frame scheduling.
- Surface damage.
- Unnecessary full-screen repaint.
- Scaling.
- Compositor effects.
- Layer ordering.
- Framebuffer capture overhead.

Do not set `damage-whole` or full-output repaint as a default performance fix.

Do not disable damage tracking blindly.

Do not force an older synchronization mode without evidence.

Do not set `WLR_RENDERER` or other environment variables simply because they appear in modern wlroots documentation. Verify support and behavior in this actual build.

Debug options are not production performance settings.

## 24.5 Framebuffer bridge

Preserve the established architecture:

```text
Phoc/Wayland
    |
    v
zwlr_screencopy
    |
    v
nuxel-wl-fb
    |
    v
/dev/fb0
    |
    v
Samsung DECON/AMOLED
```

`nuxel-wl-fb` remains the sole `/dev/fb0` writer.

Inspect:

- Capture frequency.
- Damage regions.
- Buffer reuse.
- Copy/scale time.
- Memory alignment.
- Stride.
- Buffer format conversion.
- Cache behavior.
- Frame skipping.
- Backpressure.
- Pan success.
- Unnecessary copies.
- Repeated full-screen transfers.

The prior baseline included a CPU copy/scale cost around 20–38 ms per blit. Verify the current measurement before using it.

Optimize without introducing a second framebuffer writer or unverified KMS path.

Do not falsely claim zero-copy.

## 24.6 Remove unnecessary visual effects

Remove or reduce effects that do not materially improve usability:

- Heavy shadows.
- Blur.
- Excessive transparency.
- Backdrop filters.
- Parallax.
- Large animated gradients.
- Decorative scaling.
- Complex page transitions.
- Repeated animations.
- Unnecessary opacity fades.
- Large animated visualizers.

Preserve useful feedback:

- Button press state.
- Focus state.
- Drag preview.
- Progress.
- Menu open/close.
- App transition where lightweight.

The desired style is fast and smooth, not visually dead.

Keep text readable.

Do not remove important animation that conveys state.

Do not use blur as a substitute for good visual hierarchy.

## 24.7 Image optimization — never degrade quality

Inspect the actual `assets/` and PWA assets.

Identify:

- Large images.
- Duplicate images.
- Oversized images.
- Unoptimized PNGs.
- SVGs with excessive metadata.
- Repeated copies of the same image.
- Large assets loaded unnecessarily.

Optimize without quality loss.

Preferred:

- Lossless PNG optimization.
- Lossless WebP where supported.
- SVG optimization that preserves rendered appearance.
- Lossless metadata cleanup.
- Deduplication of identical files.

Do not:
- Downscale UI icons without need.
- Re-encode photographs with visible loss.
- Reduce image dimensions merely to save memory when they are needed at that size.
- Strip required SVG features.
- Break transparency.
- Change asset color profiles or gamma unexpectedly.
- Convert assets to formats unsupported by the installed WebKit/GTK stack.

Preserve originals and compare.

Where possible use pixel-equivalence checks for lossless raster conversions.

Test actual rendering on Nuxel.

## 24.8 Caching and asset loading

Improve:

- Icon lookup.
- Sound metadata.
- App discovery.
- Widget resources.
- CSS/JS bundles.
- Static asset caching.
- Font caches.
- Image decoding.

Avoid:

- Unbounded memory caches.
- Duplicate caches.
- stale theme assets.
- Cache invalidation bugs.
- Synchronous asset reads on UI thread.

Use reasonable cache budgets for the phone.

## 24.9 Smoothness acceptance

Run the same before/after workload:

- Scrolling launcher.
- App drawer.
- Opening Settings.
- Switching desktop.
- Moving icons.
- Opening widgets.
- Doom controls.
- Gallery.
- WebKit page.
- Native GTK app.
- Flatpak app.

Report actual results.

A performance tweak that improves average time but introduces worse stutter must not be accepted blindly.

---

# 25. Deep audit and additional issue discovery

After implementing the explicit requests, inspect the related system for other defects.

Prioritize:

- Audio and sound.
- Clock scheduling.
- Device volume.
- Dock.
- App drawer.
- Widgets.
- Desktop layout.
- Icon movement.
- Calendar.
- Notes.
- Recorder.
- Software.
- NuXtore.
- Media Downloader.
- Doom.
- Vesktop.
- GTK.
- Flatpak.
- GPU memory.
- Phoc.
- Wayland.
- Framebuffer bridge.
- Settings.
- systemd.
- App lifecycle.

Classify findings:

- Critical.
- High.
- Medium.
- Low.
- Informational.

For each, include reproduction, evidence, cause and safe fix.

Fix high-confidence issues related to this task.

Do not expand into unrelated kernel or firmware changes.

---

# 26. Deployment and rollback

This is a userspace project.

Do not flash the kernel.

Do not start TWRP.

Do not modify bootloader, recovery, modem or device firmware.

Use Wi-Fi SSH with the specified identity.

Before every deployment stage:

- Back up affected files.
- Preserve user data.
- Validate syntax/build.
- Check service dependencies.
- Prepare rollback.
- Confirm SSH survives.

Deploy incrementally.

Do not restart all of Phoc, Bridge, sound and desktop services at once.

Use the minimum appropriate service reload/restart.

Keep the phone bootable and accessible.

---

# 27. Test matrix

The actual physical S10+ must pass the following.

## Audio

- [ ] Speaker works.
- [ ] Headphone output works where supported.
- [ ] Microphone captures real audio.
- [ ] Alarm plays.
- [ ] Timer plays.
- [ ] Volume sound plays promptly.
- [ ] Settings preview works.
- [ ] Custom sound works.
- [ ] Boot sound assignment works.
- [ ] Sound choices persist.

## Software transactions

- [ ] Installation shows progress.
- [ ] Completion explicitly says Installed.
- [ ] Removal shows progress.
- [ ] Completion explicitly says Removed.
- [ ] Failure is visible.
- [ ] Actual backend state verified.
- [ ] No checkbox-only success indication.

## Desktop

- [ ] Dock stable.
- [ ] Widgets selectable.
- [ ] Widgets placeable.
- [ ] Two existing desktops preserved.
- [ ] Add desktop works.
- [ ] Icons move.
- [ ] Grid snapping works.
- [ ] Edge-dwell desktop switching works.

## Calendar/Notes

- [ ] Notes persist.
- [ ] Notes preview.
- [ ] Convert to Calendar event.
- [ ] Calendar creates events.
- [ ] Calendar edits/deletes events.
- [ ] Reminders persist.
- [ ] Correct Nuxel numeric keyboard only.

## Doom

- [ ] Left D-pad walking works.
- [ ] Right D-pad aiming works.
- [ ] Same size.
- [ ] Same height.
- [ ] Fire below each D-pad.
- [ ] Each fire button works separately.
- [ ] Simultaneous movement/aim/fire works.
- [ ] Old Left/Right buttons removed.
- [ ] Other obsolete button removed.
- [ ] Map button works.
- [ ] Game survives control transitions.

## Recorder

- [ ] Microphone available.
- [ ] Actual sound captured.
- [ ] No startup glitch.
- [ ] Waveform matches recording.
- [ ] Save/playback works.

## Media

- [ ] yt-dlp metadata.
- [ ] MP3.
- [ ] MP4.
- [ ] Chrome cookies.
- [ ] Firefox cookies.
- [ ] Nuxel cookie adapter or honest unavailable state.
- [ ] Cancellation.
- [ ] Gallery integration.

## Performance

- [ ] Baseline recorded.
- [ ] Phoc/wlroots versions identified.
- [ ] Mali remains active.
- [ ] No software fallback.
- [ ] Effects simplified where unnecessary.
- [ ] Images optimized losslessly.
- [ ] App startup measured.
- [ ] Frame pacing measured.
- [ ] Before/after results recorded.

## Vesktop

- [ ] Correct ARM64 binary.
- [ ] Application launches.
- [ ] UI usable.
- [ ] Owner logs in manually.
- [ ] Session persists.
- [ ] No credential leakage.

---

# 28. Deliverables

The final implementation report must provide:

1. Root-cause analysis for every issue.
2. Active source/runtime map.
3. Changed source files.
4. Changed configs.
5. Asset migration record.
6. Sound-manager architecture.
7. Audio playback/capture results.
8. Alarm/timer/volume timing.
9. Dock flicker evidence.
10. DevMgmt graphics diagnostics.
11. Tab text fix.
12. GPU memory metric source and percentage denominator.
13. GTK/Flatpak startup benchmarks.
14. yt-dlp version and test report.
15. Cookie-adapter security report.
16. Notes/Calendar persistence evidence.
17. Widget registry and layout persistence.
18. Icon drag/cross-desktop results.
19. Doom control layout and physical test.
20. Software install/removal transaction implementation.
21. Recorder microphone/waveform results.
22. Vesktop version/architecture/login report.
23. Performance optimization before/after report.
24. Image optimization and visual-integrity report.
25. Additional audit findings.
26. Deployment/rollback instructions.

Distinguish:

- Automated tests.
- Host tests.
- Physical S10+ tests.

Never claim a physical test passed if it was not performed.

---

# 29. Final definition of done

PWNAGE-82000 is finished only when:

### Audio

- Audio output works globally.
- Microphone capture works.
- Alarm/timer work.
- Volume feedback works immediately.
- Sound settings work.
- Custom sound discovery works.
- Files are correctly stored in `~/Sounds/`.
- Repository assets use `./assets/nuxel-sounds/`.

### Desktop

- Dock does not flicker.
- Widgets are visible and placeable.
- Desktops can be managed.
- Icons can move and snap.
- Dragging across desktops works.
- GPU memory meter is accurate.
- Hardware diagnostics are truthful.
- DevMgmt tabs are readable.

### Applications

- Native GTK and Flatpak apps start faster.
- Software reports operation completion accurately.
- Calendar events persist.
- Notes persist.
- Notes-to-Calendar works.
- Recorder captures and displays real audio.
- Vesktop runs on ARM64.
- Media Downloader uses yt-dlp properly.

### Doom

- Twin D-pads present.
- Left D-pad moves.
- Right D-pad aims.
- Both aligned at the same height.
- Matching Fire button below each.
- Old Left/Right and obsolete auxiliary buttons removed.
- Map button operational.
- Fresh NuXtore install works.

### Performance

- Mali remains functional.
- Phoc remains accelerated.
- No software renderer regression.
- Frame pacing improves or any limitation is explained.
- Effects are simplified.
- Assets are optimized without visual degradation.
- Framebuffer bridge is stable.
- One `/dev/fb0` writer remains.

### Safety

- User data preserved.
- No unnecessary kernel changes.
- No TWRP modification.
- SSH remains functional.
- No credentials or cookies leaked.
- No weakening of Flatpak sandboxing.

---

# 30. Final instruction to the implementation agent

This is a real Nuxel integration milestone.

Connect to the physical S10+ over Wi-Fi SSH using:

```text
~wicked/.ssh/wicked_wqn_id_rsa
```

Use the existing Nuxel connection workflow to discover the current host.

Start by restoring real audio playback and capture.

Do not create a new sound settings UI until the actual audio stack works.

Move the complete sound collection into:

```text
./assets/nuxel-sounds/
```

and install it into:

```text
~/Sounds/
```

Make Clock, volume feedback, Recorder and future events use a central sound manager.

Finish Calendar and Notes with real persistent data.

Implement real widgets and draggable desktop icons.

Make the Software app report actual installation/removal results.

Give Doom the symmetric dual-thumb control layout with working Map and two identical Fire buttons.

Carry out a measured Mali/Phoc performance optimization round.

Remove unnecessary fancy effects, but preserve clarity and useful feedback.

Optimize assets without degrading their original image quality.

Do not apply random compositor flags, disable damage tracking or force software rendering.

Do not call the phone fully accelerated without proving every required stage.

Do not sacrifice sound, touch, desktop stability or recovery to chase a benchmark.

**PWNAGE-82000 is complete only when the S10+ is demonstrably smoother, audio works, all the listed applications and desktop features function correctly, the Doom controls feel natural with two thumbs, and all changes are integrated into the actual running Nuxel image.**
