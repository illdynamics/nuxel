# PWNAGE-82000 — Nuxel Performance, Desktop, Sound and Application Completion
## Twin-D-pad Doom controls, software installation feedback, GPU/compositor optimization, audio recovery, widgets, Calendar, Notes, Recorder and applications

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**OS:** Fedora-based Nuxel ARM64  
**Desktop:** Phoc/Wayland, custom Nuxel shell  
**GPU:** Mali-G76 MC12  
**Deployment:** Wi-Fi SSH, root console  
**SSH identity:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Priority:** Critical  
**Starting state:** Boot normally into Nuxel  
**TWRP/kernel flash:** Not required. Do not reflash for these userspace tasks.

### 1. Connect to Nuxel

Discover the current Wi-Fi SSH address using the existing Nuxel scripts and connection configuration. Do not invent an IP.

Use:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  -o ServerAliveInterval=15 \
  root@<DISCOVERED_NUXEL_WIFI_HOST>
```

Verify the host identity and root access. Preserve host-key verification. Do not copy or display the private key.

### 2. Doom — redesign the mobile controls

Implement a symmetrical twin-D-pad control layout.

**Left side:**
- Left D-pad for walking/movement.
- Fire button directly underneath it.

**Right side:**
- Right D-pad for aiming/look direction.
- Fire button directly underneath it.

Both D-pads must:

- Be the same size.
- Be aligned at the exact same vertical height.
- Have equivalent touch response.
- Have appropriate dead zones and movement sensitivity.
- Work simultaneously with the other hand's controls.

Both fire buttons must:

- Be identical in size.
- Be positioned directly below their respective D-pad.
- Trigger the same actual Doom fire action.
- Work independently.
- Support holding for continuous fire if the engine supports it.

The player must be able to fire with either thumb.

#### Remove old controls

Inspect the current Doom HUD.

Remove the old separate Left and Right buttons.

Remove the other obsolete auxiliary button(s) currently shown alongside the Map control.

Keep only the Map button from the old auxiliary control group.

Do not accidentally remove the new fire buttons.

#### Map button

Make the Map button functional.

It must open the actual Doom automap, not a fake Nuxel overlay.

Verify:

- Map appears.
- Map updates correctly.
- Touch input works.
- Map closes/toggles correctly.
- Returning to gameplay preserves the current game state.
- Buttons do not remain stuck after closing the map.

#### Controls and HUD quality

- Keep controls inside the safe screen area.
- Preserve proportional layout in landscape and other supported orientations.
- Keep the two D-pads aligned.
- Keep both fire buttons aligned beneath them.
- Avoid overlapping the game viewport unnecessarily.
- Prevent accidental gestures from reaching the desktop.
- Support simultaneous movement, aiming and firing.
- Add appropriate sensitivity/dead-zone configuration where useful.

Do not replace original Doom graphics with redesigned artwork.

### 3. Software app — real installation/removal feedback

The Software app currently displays only messages such as:

- Installing...
- Removing...

The user has no reliable confirmation when the operation actually finishes. A checkbox appearing/disappearing is insufficient.

Implement explicit transaction status.

Required states:

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

Show:

- Application name.
- Operation.
- Current state.
- Progress where available.
- Completion result.
- Failure reason.
- Retry action where appropriate.

On successful installation:

- Show a visible success confirmation such as `Installed`.
- Verify the application is actually installed.
- Refresh the application list.
- Refresh launcher exports.
- Update the checkbox/state.
- Allow immediate launch.

On successful removal:

- Show `Removed`.
- Verify the application ref is actually gone.
- Refresh the list.
- Remove stale launcher entries.
- Update the checkbox/state.

On failure:

- Keep accurate installation state.
- Show the actual error.
- Do not show success.
- Provide a retry option.

Do not treat an HTTP/Bridge request acceptance as proof that Flatpak finished.

Use a transaction ID and backend operation state. Handle cancellation and interrupted operations correctly.

### 4. Restore the complete sound system

Sound currently appears broken globally.

Diagnose the actual audio backend, output devices, capture devices, services, routes, permissions and decoder dependencies first.

Test speaker playback with a known-good WAV and MP3. Test microphone capture separately.

Do not create the Sounds settings UI before restoring working playback.

Use the existing audio architecture. Do not start a second audio server.

### 5. Sound assets and user sound library

The repository should use:

```text
./assets/nuxel-sounds/
```

Move the existing `nuxel-pow.mp3` and `nuxel-alarm.mp3` into the original `./nuxel-sounds` collection, then move the complete collection into `./assets/nuxel-sounds/`.

Install all supplied sounds into:

```text
~/Sounds/
```

Preserve user custom sounds and avoid destructive overwrites.

Implement a central Nuxel sound manager.

Add per-event sound assignments in Settings:

- Volume change.
- Boot-up.
- Alarm.
- Timer.
- Incoming messages.
- Notifications.
- Future events.

Requirements:

- Automatically discover new MP3 and other supported sound files.
- Refresh the selectable list.
- Show metadata.
- Preview each sound.
- Browse custom files separately for each assignment.
- Validate playback compatibility.
- Save choices persistently.
- Handle deleted/renamed files.
- Use one shared playback API across Nuxel.

### 6. Clock alarms and timers

Make Clock play the selected alarm/timer sound.

Default:

```text
~/Sounds/nuxel-alarm.mp3
```

Resolve the asset through the installed sound manager, not a relative working-directory path.

Alarms must continue to work when Clock is backgrounded or closed, through the proper Nuxel scheduling service.

Test actual audio on the phone speaker.

### 7. Volume-change sound

Restore volume feedback and use the selected sound.

Default:

```text
nuxel-pow.mp3
```

Preload/decode the sound and reuse a warm output path.

Target audible playback within approximately 100 ms of a normal volume-change event.

Avoid:

- Spawning a new decoder for every event.
- Restarting the audio server.
- Blocking the volume slider.
- Stale queued sounds.
- Excessive replay when rapidly dragging the volume control.

Measure actual time to audible playback.

### 8. DevMgmt graphics diagnostics

Add detailed graphics acceleration information.

Report separately:

- Mali kbase.
- `/dev/mali0`.
- EGL vendor/version/renderer.
- GLES.
- Phoc renderer.
- WebKit GPU rendering.
- WebKit DMA-BUF transport.
- DRM device discovery.
- VGEM.
- GBM import.
- linux-dmabuf formats/modifiers.
- Phoc import.
- Framebuffer bridge.
- Physical presentation.
- CPU final copy/scale.

Use truthful states:

- FULL.
- PARTIAL.
- UNAVAILABLE.
- DEGRADED.
- NOT TESTED.

Do not report full acceleration merely because Mali rendering works.

Fix DevMgmt tabs so text no longer overlaps in portrait or landscape.

### 9. GPU memory/VRAM meter

Display GPU memory usage as amount plus percentage by default.

Add Home Settings choices:

- Amount + percentage (default).
- Percentage only.
- Amount only.

Persist settings.

The S10+ Mali GPU uses shared system memory. Do not invent a dedicated VRAM capacity.

Calculate a percentage only when a real allocation/budget pair is available and the denominator is meaningful. Otherwise display the amount and honestly state that percentage is unavailable.

### 10. GTK and Flatpak performance

Measure native GTK and Flatpak startup:

- Launcher request.
- Process spawn.
- D-Bus.
- Bubblewrap.
- Namespace creation.
- Runtime setup.
- Dynamic linker.
- GTK/libadwaita.
- Fontconfig.
- Icon/theme lookup.
- Portal activation.
- Wayland connection.
- First frame.

Run cold and warm tests.

Fix measured bottlenecks without disabling Flatpak sandboxing or leaving every app running in the background.

### 11. yt-dlp Media Downloader

Use yt-dlp as the download engine.

When a user pastes a URL:

- Validate URL.
- Retrieve metadata.
- Show title, duration, thumbnail and formats.
- Select format.
- Select cookie source.
- Download.
- Show real progress.
- Support cancellation.
- Save to Downloads.
- Refresh Gallery.

Formats:

```bash
yt-dlp -t mp3 "<URL>"
yt-dlp -t mp4 "<URL>"
```

Use the installed version's supported preset behavior and FFmpeg/FFprobe dependencies.

Cookie source selector:

- Chrome.
- Firefox.
- Nuxel.
- None.

Chrome/Firefox should use native yt-dlp support where installed.

Nuxel is not a built-in yt-dlp browser identifier. Implement a real secure WebKit cookie export adapter if available. Otherwise mark Nuxel unavailable.

Use a private temporary Netscape-format cookie file where needed. Never log or expose cookies. Remove temporary cookie files after download.

Use subprocess argument arrays, not shell string concatenation.

Respect site permissions and do not bypass DRM/access controls.

### 12. Notes

Make Notes persistent.

Save all notes under:

```text
~/Notes/
```

Support:

- Create.
- Edit.
- Autosave.
- Explicit save.
- Rename.
- Delete with confirmation.
- Search.
- Preview.
- Reopen after reboot.

Show notes in a Gallery-style card/grid view.

Add actions:

- Convert to alarm.
- Convert to Calendar event.
- Add reminder.

Use the same Calendar/alarm backend. Confirm extracted dates and times before creating records.

### 13. Calendar

Fix event creation completely.

Support:

- Create.
- Edit.
- Delete.
- View details.
- Title.
- Description.
- Start/end date.
- Start/end time.
- All-day.
- Reminders.
- Persistence.
- Time-zone handling.

Use a single stable event model and data service.

Verify a saved event survives closing/reopening Calendar and rebooting.

Ensure Notes-to-Calendar conversion creates the same event records the Calendar app can edit.

### 14. Calendar keyboard

Remove the unwanted dark-blue duplicate keyboard completely from the active implementation.

Use the exact existing grey/blue/black/white Nuxel keyboard used by the Clock app's hour fields.

Calendar date/time fields must request the correct numeric/time layout.

Ensure:

- Only one keyboard surface appears.
- Back dismisses keyboard first.
- Swipe down dismisses keyboard.
- Navigation remains accessible.
- Force-closing Calendar releases its input context.

Do not implement a separate Calendar keyboard.

### 15. Desktop widgets and desktops

Holding an empty desktop background must open a context menu:

- Home Settings.
- Widgets.

Do not directly open Home Settings.

The Widgets option opens a picker of real available widgets.

Create a widget registry with stable IDs, metadata, rendering components, size information and data sources.

Allow selecting a widget and placing it on either desktop.

Preserve the existing two desktops.

Add Home Settings support for:

- Add desktop.
- Remove desktop.
- Reorder/rename where supported.
- Select default desktop.
- Configure desktop count.

Never erase desktop content silently when removing a workspace.

### 16. Desktop icon movement

Make app icons genuinely draggable.

Requirements:

- Long-press enters drag mode.
- Icon follows touch.
- Grid snapping.
- No overlap.
- Clear drop target.
- Persistent positions.

When dragged to the left/right screen edge and held for approximately one second:

- Switch to previous/next desktop.
- Keep the dragged icon attached.
- Allow dropping on the new desktop.

Use edge dwell, hysteresis and a visual indicator.

Avoid conflicts between background long-press, icon dragging, tapping and resizing.

### 17. Dock flicker

Fix intermittent flickering of the four bottom docked apps.

Inspect rendering lifecycle, DOM identity, layer stacking, duplicate listeners, app discovery updates, transitions and repainting.

Do not remove the four pinned apps or reset their order.

Use stable identities and minimal updates.

Test Home, drawer, rotation, app launch/close, desktop switching and lock/unlock.

### 18. Doom mobile controls — twin-D-pad layout

Implement the new mobile Doom HUD.

<pre>
       LEFT SIDE                     RIGHT SIDE

     WALK D-PAD                     AIM D-PAD
       [  ↑  ]                       [  ↑  ]
       [← ↓ →]                       [← ↓ →]

      [ FIRE ]                       [ FIRE ]

       movement                        aim
</pre>

This is a conceptual layout; implement the actual touch visual design consistent with Nuxel.

#### Left D-pad — walking

- Dedicated movement control.
- Same size as right D-pad.
- Supports directional movement.
- Responsive continuous movement while held.

#### Right D-pad — aiming

- Dedicated look/aim control.
- Same size as left D-pad.
- Supports horizontal and vertical look movement.
- Configure sensitivity and dead zone.
- Do not move the player when aiming.
- Do not rotate the system display.

#### Alignment

Both D-pads must be:

- Identical in size.
- Aligned at exactly the same vertical height.
- Equally spaced from their respective screen edges.
- Positioned safely within the gameplay area.
- Responsive in portrait/landscape as supported by the game's layout.

#### Fire buttons

Place one fire button directly below each D-pad.

Both fire buttons must:

- Be identical in size.
- Have the same visual style.
- Be positioned at the same relative distance from their corresponding D-pad.
- Trigger exactly the same game fire action.
- Work independently.
- Support held/continuous firing where supported.

This lets the user fire with either thumb.

Test simultaneously:
- Left-thumb movement.
- Right-thumb aiming.
- Either fire button.

The engine input path must support multi-touch without cancelling one control when another is touched.

#### Remove old buttons

Inspect the current Doom HUD.

Remove the old separate Left and Right buttons.

Remove the obsolete auxiliary button(s) presently alongside Map, except the Map button.

Keep only Map from that legacy group.

Do not remove either of the two new Fire buttons.

#### Map button

Make Map functional.

It must open the actual Doom automap.

Verify the map updates, accepts required input, closes correctly and returns to gameplay without losing the current game state.

#### Packaging and game data

Keep Nuxel Doom installable completely through NuXtore.

Inspect Chocolate Doom's role. Do not remove an engine dependency Nuxel Doom requires, but remove the redundant standalone user-facing Chocolate Doom entry if unnecessary.

Bundle only legally redistributable WADs. Provide import for the owner's own legally obtained WADs.

Preserve original Doom graphics.

### 19. Recorder

Fix microphone capture and the opening glitch.

Inspect capture backend, device, permissions, route, sample rate, format, input gain and stream initialization.

Prove real PCM samples arrive.

Display a waveform calculated from actual recorded audio.

Use downsampled peak/RMS data.

Show live waveform where practical and completed waveform after saving.

Provide duration, playback position and controls.

Save recordings persistently and expose them to Gallery.

Waveform failure must not destroy the recording.

### 20. Software app keyboard

The Software app currently opens with the keyboard visible and cannot reliably reveal navigation or dismiss the keyboard.

Fix using shared Nuxel keyboard/navigation infrastructure.

- Swipe up reveals Back/Home/Tabs.
- Swipe down from the keyboard dismisses it.
- Back dismisses keyboard before app navigation.
- No duplicate keyboard.
- Focus is cleared when leaving the app.

### 21. Vesktop

Make Vesktop launch and work on Nuxel ARM64.

Inspect the installed package and current official releases.

Verify binary architecture, dependencies, Electron/Chromium runtime, Wayland support, scaling, audio, notifications and app lifecycle.

Prefer a compatible native Fedora ARM64 package if available and appropriate.

Do not install x86_64 or require emulation.

Do not weaken sandboxing unnecessarily.

The owner must complete login interactively. Do not place passwords, QR data, tokens or credentials into scripts/logs.

Verify session persistence without exposing account secrets.

### 22. Performance boost round — smoothness and responsiveness

After functional fixes, conduct a measured system-wide optimization round.

Baseline first:

- Frame time.
- Frame pacing.
- Dropped frames.
- CPU/GPU load.
- Memory.
- Startup time.
- Input-to-visible-response latency.
- Framebuffer copy/scale time.
- Power/thermal behavior where safely measurable.

Identify the actual Phoc, wlroots, Mesa, Mali and WebKit versions.

Do not blindly set compositor environment variables or copy tuning flags from another wlroots/Phoc version.

Inspect only settings actually supported by the installed versions.

Optimize:

- Phoc rendering.
- Damage tracking.
- Buffer allocation.
- Mali usage.
- Framebuffer bridge.
- WebKit rendering.
- PWA repainting.
- GTK startup.
- Image loading.
- Icon caching.
- Widget refresh.
- Dock rendering.
- Animation and visual effects.

Remove unnecessary:

- Blur.
- Heavy shadows.
- Large transparency layers.
- Complex gradients.
- Excessive transitions.
- Parallax.
- Decorative scaling/zoom effects.
- Repeated backdrop filters.
- Large animated decorations.

Preserve usability and visual quality.

Use simple responsive transitions where useful. The goal is smoothness, not removing all visual feedback.

#### GPU/compositor safety

The known physical architecture is:

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

`nuxel-wl-fb` must remain the sole `/dev/fb0` writer.

Preserve Mali kbase and the working EGL/Phoc path.

Do not enable an unverified DRM/KMS display stack.

Do not force a software renderer.

Do not enable unsupported buffer modifiers.

Do not introduce a second framebuffer writer.

#### Animation policy

Inspect the installed Phoc version and whether its build supports an animation-disable option.

Use documented, actually supported controls only.

Do not assume flags from current upstream wlroots exist in Nuxel's installed older version.

Remove heavy Nuxel shell effects at their source where appropriate.

#### Image optimization

Compress images only when quality is preserved.

Prefer:

- Lossless PNG optimization.
- Lossless WebP where verified.
- SVG optimization that preserves appearance.
- Lossless metadata cleanup where appropriate.

Do not downscale icons or UI assets unnecessarily.

Do not introduce lossy image re-encoding.

Preserve originals and compare output visually and by pixel equivalence where practical.

Verify transparency, color, dimensions and orientation.

Use optimized assets only after testing them in the actual WebKit/GTK runtime.

### 23. Deep audit

Inspect additional related defects across:

- Audio.
- Settings persistence.
- NuXtore.
- Desktop dock.
- Widgets.
- App lifecycle.
- Calendar.
- Notes.
- Recorder.
- Media.
- Doom.
- GTK/Flatpak.
- Vesktop.
- Phoc.
- Wayland surfaces.
- Framebuffer bridge.
- systemd services.

Fix high-confidence issues within this scope.

Record unrelated findings in a separate prioritized backlog.

### 24. Mandatory acceptance

- [ ] Audio playback works globally.
- [ ] Microphone capture works.
- [ ] Clock alarm plays.
- [ ] Clock timer plays.
- [ ] Volume sound works with low latency.
- [ ] All supplied sounds are installed in `~/Sounds/`.
- [ ] Repository layout is `./assets/nuxel-sounds/`.
- [ ] Sound Settings work.
- [ ] New MP3s are detected.
- [ ] Browse custom files works.
- [ ] Four dock icons are stable.
- [ ] DevMgmt graphics diagnostics are accurate.
- [ ] DevMgmt tab labels do not overlap.
- [ ] GTK/Flatpak startup improves measurably.
- [ ] GPU memory display is truthful.
- [ ] Hardware meter amount/percentage setting works.
- [ ] yt-dlp MP3 and MP4 workflows work.
- [ ] Cookie selection is safe and functional.
- [ ] Notes save under `~/Notes/`.
- [ ] Notes Gallery-style preview works.
- [ ] Notes-to-Calendar conversion works.
- [ ] Calendar creates/edits/deletes events.
- [ ] Calendar uses one correct Nuxel numeric keyboard.
- [ ] Widgets are selectable and placeable.
- [ ] Desktops can be added/managed.
- [ ] App icons drag and snap to grid.
- [ ] Edge-dwell desktop switching works.
- [ ] Doom has two aligned D-pads.
- [ ] Doom has two identical Fire buttons.
- [ ] Old Left/Right and obsolete buttons are removed.
- [ ] Doom Map works.
- [ ] Doom installs with legal WAD handling.
- [ ] Recorder captures real audio.
- [ ] Recorder waveform is real.
- [ ] Software keyboard/navigation works.
- [ ] Vesktop launches on ARM64.
- [ ] Owner can complete Vesktop login.
- [ ] Performance improvements are measured.
- [ ] No regression to existing Nuxel features.

### Deliverables

- Root-cause report for every issue.
- Complete modified source/config/build file list.
- Central sound manager and asset migration.
- Clock/volume/Recorder audio evidence.
- DevMgmt acceleration report.
- Startup performance benchmark.
- VRAM metric source and denominator.
- yt-dlp integration and cookie security report.
- Notes/Calendar persistence evidence.
- Widget/desktop layout implementation.
- Doom control implementation and fresh-install test.
- Software transaction status implementation.
- Vesktop architecture and login test.
- Performance optimization report.
- Additional audit findings.
- Reversible deployment and rollback instructions.

**Definition of done:** The physical S10+ feels smoother and more responsive, the audio system works, desktop/widgets and application features are genuinely usable, Doom has the new dual-thumb controls, and installation/removal operations provide clear verified results.
