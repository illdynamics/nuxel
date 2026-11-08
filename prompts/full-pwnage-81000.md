# FULL PWNAGE-81000 — Nuxel Mobile OS Integration and Quality Completion
## Live-console state, desktop/app drawer, unified sound manager, Clock, DevMgmt acceleration diagnostics, GTK/Flatpak performance, Gallery, yt-dlp, Recorder waveform, Adwaita appearance, Software keyboard, Signal and comprehensive reliability audit

**Project:** Nuxel — Mobile Linux for Control Freaks  
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**Architecture:** ARM64  
**OS:** Fedora-based Nuxel  
**Desktop:** Phoc/Wayland with custom Nuxel shell and framebuffer presentation bridge  
**Deployment:** Wi-Fi SSH, root console  
**SSH key:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Priority:** High  
**Starting state:** Phone booted normally into Nuxel  
**TWRP:** Not required  
**Kernel reflash:** Not expected; do not reflash for these userspace issues

---

# 0. Mission

Complete a substantial set of Nuxel usability, media, sound, application and diagnostics improvements.

The user has identified multiple remaining issues and requested a deeper audit to uncover additional related defects.

Treat this as one coordinated integration and reliability task.

Do not simply patch the visible symptom in each app.

Investigate shared owners and common infrastructure:

- Session/console state.
- Sound playback and event routing.
- Application discovery and drawer layering.
- Clock scheduling and background execution.
- Graphics capability reporting.
- Application startup pipeline.
- Gallery navigation.
- Media download lifecycle.
- Recorder data visualization.
- Desktop appearance/settings propagation.
- Keyboard/navigation handling.
- Signal ARM64 packaging/runtime compatibility.

Preserve existing working Nuxel functionality.

The end result should be a cohesive mobile OS experience with correct app integration, reliable media behavior and accurate system diagnostics.

---

# 1. SSH connection and target verification

The agent must connect to the running physical S10+ through Wi-Fi SSH.

The owner expects the agent to have root-console access.

## 1.1 Required identity

Use:

```text
~wicked/.ssh/wicked_wqn_id_rsa
```

Do not generate a replacement key.

Do not reveal or copy the private key.

Check that the key is readable:

```bash
test -r ~wicked/.ssh/wicked_wqn_id_rsa
```

## 1.2 Discover current Wi-Fi host

Do not use a stale remembered IP address.

Inspect:

- Existing SSH configuration.
- Existing known_hosts.
- Current Nuxel connection scripts.
- Existing S10+ debug tooling.
- Current device network status.
- Existing Wi-Fi SSH configuration.

A known helper is:

```text
scripts/s10plus-debug-pack/nuxel-live-ssh.sh
```

Inspect its supported options and use its Wi-Fi transport discovery/status functionality if appropriate.

For example:

```bash
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
    --transport wlan \
    --status
```

Use the actual repo path and syntax.

## 1.3 Connect

Once the host is proven:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
    -o IdentitiesOnly=yes \
    -o BatchMode=yes \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=15 \
    root@<DISCOVERED_NUXEL_WIFI_HOST>
```

Preserve SSH host-key verification.

Do not disable host-key validation to bypass an identity mismatch.

Verify:

```bash
id
whoami
hostname
uname -a
```

Confirm root privileges.

Do not modify networking, SSH, Wi-Fi or firewall behavior unnecessarily.

Maintain a persistent/reliable SSH session while working.

Do not restart SSH or networking as a shortcut.

---

# 2. Initial repository and runtime audit

Identify the real active source and runtime implementation for every requested feature.

Inspect:

- Home/desktop shell.
- App drawer.
- Dock.
- Live-console indicator.
- Console state/Bridge.
- Clock.
- Alarm/timer backend.
- Audio playback service.
- Volume control.
- Sound assets.
- Sound settings.
- DevMgmt.
- Graphics diagnostics.
- GTK/Flatpak application launch.
- Hardware meters.
- Gallery.
- Media Downloader.
- yt-dlp integration, if already present.
- Recorder.
- Appearance Settings.
- GTK/libadwaita configuration.
- Software app.
- Keyboard/input method.
- Signal app/package.
- Systemd services.
- Nuxel Bridge.
- Framebuffer bridge.
- Build/install/image packaging.

The following known paths are useful starting points but may not be the complete active implementation:

```text
pwa/nuxel-home/
pwa/nuxel-apps/
services/nuxel-bridge/
tools/s10plus/
configs/nuxel/
images/s10plus/
assets/
```

Search for every relevant component rather than assuming a particular file is authoritative.

## 2.1 Prove active code paths

For each changed feature, identify:

- Source file.
- Runtime process.
- Owning service.
- Installed path.
- Build target.
- Configuration.
- IPC/API contract.
- Logs.
- Package integration.

A correct patch to a file that is not installed or executed is not a fix.

## 2.2 Preserve the baseline

Before changes:

- Check Git state.
- Identify local modifications.
- Back up files that will be replaced.
- Record current service definitions.
- Record active audio backend.
- Record current application entries.
- Record app drawer layout.
- Capture useful baseline screenshots.
- Record startup timings.
- Record current GPU capability evidence.

Do not overwrite local owner changes.

Use a tracked branch or reversible patch set.

---

# 3. Fix live-console indicator state

## 3.1 Current issue

The live-console indicator is now permanently visible.

It should only appear when the owner is actually using one of the external Nuxel SSH console modes:

- USB SSH Console.
- Wi-Fi SSH Console.

The icon representing the console type underneath it is already working correctly.

Preserve that existing behavior.

When the phone is being used directly through its touchscreen, without an external console client, the live-console indicator must not be visible.

## 3.2 Correct state ownership

Find the service/Bridge/UI that owns console-session information.

Do not infer active console state merely from:

- An SSH daemon running.
- An SSH process existing.
- An administrative root shell.
- Any arbitrary remote TCP connection.
- The agent's own maintenance SSH connection.
- A background diagnostic session.

The indicator must represent an actual external console session, not simply that remote access is enabled.

Use a session-specific registration/state contract.

A valid active console session should identify:

- Session ID.
- Console type.
- USB/Wi-Fi transport.
- Start time.
- Active/disconnected state.
- Associated foreground console application/client.

The current console-type icon may reuse this data.

## 3.3 Agent SSH must not create false console state

The agent itself will connect over Wi-Fi SSH to administer Nuxel.

That connection must not automatically cause the phone's live-console indicator to become visible unless it is explicitly using the user-facing Wi-Fi SSH Console session.

Separate:

- Administrative SSH access.
- Debugging/maintenance SSH.
- User-facing USB SSH Console.
- User-facing Wi-Fi SSH Console.

This distinction is mandatory.

## 3.4 Session lifecycle

When a real console starts:

- Register session.
- Show the live-console indicator.
- Show the appropriate console-type icon.

When it disconnects:

- Clear session.
- Hide live-console indicator.
- Restore ordinary local desktop appearance.

Handle:

- Clean disconnect.
- Network loss.
- USB disconnect.
- Client crash.
- Phone reboot.
- Stale session cleanup.

Do not leave a persistent stale indicator after a console exits.

---

# 4. Fix app drawer dock contamination and bottom-row flicker

## 4.1 Current issue

The four docked desktop app icons appear at the bottom of the app drawer.

This must never happen.

The app drawer is its own full application grid and must not display the four desktop dock entries as an overlay or duplicated row.

The bottom row of app drawer icons also flickers.

## 4.2 Separate desktop dock from app drawer

Identify the actual dock owner.

Check whether:

- Desktop dock remains mapped above drawer.
- Drawer does not hide dock.
- Dock is duplicated in the drawer's DOM.
- An overlay references the dock component.
- The dock layer has incorrect z-order.
- Both desktop and drawer render the same app list.
- A layer-shell surface remains active.
- A transition fails to detach the desktop dock.

Make the ownership explicit.

Opening the drawer must disable/hide the desktop dock presentation while retaining its state for return to Home.

Do not delete the four pinned applications.

Do not clear the dock configuration.

## 4.3 Diagnose flicker

Inspect:

- App list updates.
- Grid key stability.
- DOM node recreation.
- List virtualization.
- Scroll container dimensions.
- Bottom-row clipping.
- CSS transforms.
- WebKit repaints.
- Output geometry.
- Animation transitions.
- Dock overlay.
- Duplicate event listeners.
- Resize observers.
- App discovery refresh events.

Do not fix flicker with a permanent animation disable unless the animation is the actual cause.

Avoid rebuilding the entire app drawer on every minor event.

Use stable application identities and update only necessary entries.

## 4.4 Acceptance

- Open drawer.
- Scroll to bottom.
- Rotate to landscape.
- Scroll again.
- Open and close keyboard.
- Return Home.
- Reopen drawer.

At no point should the four desktop dock icons appear inside the drawer.

The bottom application row must remain stable and flicker-free.

---

# 5. Unified Nuxel sound manager

This is a central feature of PWNAGE-81000.

The owner has supplied a new folder:

```text
./nuxel-sounds
```

Inspect the actual directory and every included sound.

Do not assume a fixed set of files or silently ignore assets.

The goal is a central, extensible sound library and sound-assignment system.

## 5.1 Sound storage

Create or use a user-accessible sound directory.

Preferred visible location:

```text
~/Sounds/
```

The application-managed sound library may be stored under an internal XDG data directory, but the user must be able to browse and manage files conveniently.

For example:

```text
~/Sounds/
```

may contain:

```text
~/Sounds/Nuxel/
~/Sounds/Custom/
```

Choose a consistent organization.

Preserve original source assets in the repository and install/copy them into the user sound library.

Do not destroy the original `./nuxel-sounds` directory.

## 5.2 Discover all supplied sounds

Inspect:

- File names.
- MIME types.
- Audio format.
- Duration.
- Sample rate.
- Channels.
- Bitrate.
- Decoder compatibility.
- File sizes.
- Embedded metadata.

Include supported formats from the actual audio pipeline.

MP3 must work.

Add WAV/OGG/FLAC support only where the installed decoder stack supports them.

Do not show invalid files as selectable sounds.

## 5.3 Per-event assignments

Add a new Sounds section in Settings.

It must support individual assignments for:

| Sound action | Purpose |
|---|---|
| Volume change | Play on actual volume changes |
| Boot-up | Play after successful Nuxel startup |
| Alarm | Clock alarm |
| Timer | Countdown completion |
| Messages | Future messaging-event sound |
| Notifications | General notification sound |
| Other events | Future extensibility |

Each entry must have:

- Current selection.
- Sound title.
- Preview button.
- Browse button.
- Reset/default option.
- File validation.
- Persistent storage.

For future message/notification events, implement the assignment now but do not pretend events are wired when they are not.

## 5.4 Dynamic detection

When new sound files are added to the sound directory:

- Automatically detect them.
- Refresh the available sound list.
- Read metadata.
- Validate decoder compatibility.
- Make them available for every applicable assignment.

Use a filesystem watcher or a reliable refresh/indexing mechanism.

Avoid repeatedly rescanning large audio directories on every settings interaction.

Handle renamed and deleted files.

If a selected file disappears, fall back safely and report the missing assignment.

## 5.5 Custom file browser

Each sound assignment must include a Browse button.

Allow selecting a custom audio file from the filesystem.

Use safe file-picker integration.

The selected file should either remain at a stable user path or be copied into the managed sound library with user consent and collision-safe naming.

Do not silently copy large files without explaining behavior.

Prevent path traversal.

Validate that the selected file actually decodes.

Provide an immediate preview.

## 5.6 Sound manager architecture

Create or repair one shared Nuxel sound manager.

It should provide:

- Asset lookup.
- User assignments.
- Audio decoding.
- Playback.
- Stop/cancel.
- Volume control.
- Event routing.
- Preloading.
- Error reporting.
- Output selection where available.

Do not create separate hardcoded playback logic in Clock, volume control, boot service and notification components.

Every component should request an assigned sound through the common manager.

---

# 6. Fix Clock alarm/timer playback

## 6.1 Current issue

The Clock app's alarm and timer do not play:

```text
./assets/nuxel-alarm.mp3
```

Inspect the actual asset and the active deployed path.

Do not assume current working directory.

Resolve resources through the installed Nuxel asset manager.

## 6.2 Correct alarm architecture

The Clock app must not be the only process responsible for playing an alarm.

If the app is minimized, closed or restarted, an armed alarm must still fire according to Nuxel's supported scheduler design.

Inspect the existing timer/alarm persistence and service architecture.

Implement or repair:

- Alarm schedule storage.
- Timer lifecycle.
- Background scheduling.
- Trigger delivery.
- Sound playback.
- Stop/dismiss.
- Snooze, if supported.
- Reboot behavior according to current Nuxel design.
- Duplicate-trigger prevention.

The central sound manager should select the alarm/timer sound.

## 6.3 Playback requirements

When an alarm or timer fires:

- Sound starts promptly.
- Actual audio reaches the phone output.
- Playback continues according to alarm policy.
- Dismiss stops it.
- Repeated events do not create uncontrolled overlapping streams.
- The app UI reflects the true alarm state.
- Audio errors are surfaced.

Test with the app open, backgrounded, closed and after a reboot where scheduling semantics support it.

## 6.4 Test actual audio

Use the S10+ speaker and available headphone output.

Verify the sound file is decoded and audible.

Do not treat a successful `play()` call or a created pipeline as proof that sound reached the hardware.

Record playback start time and actual completion/stop behavior.

---

# 7. Make volume-change sound immediate

## 7.1 Current symptom

Changing volume currently takes approximately 2–3 seconds before:

```text
./assets/nuxel-pow.mp3
```

is played.

This is unacceptable for a responsive mobile UI.

## 7.2 Diagnose the delay

Instrument:

1. Volume change input.
2. System volume backend update.
3. Sound event generated.
4. Sound manager receives event.
5. Audio pipeline state.
6. Decoder start.
7. Audio output queue.
8. First audible frame.

Identify the actual delay.

Possible causes include:

- Audio pipeline initialized from scratch.
- MP3 decoder startup.
- PipeWire/PulseAudio reconnect.
- Event queue backlog.
- Synchronous bridge operation.
- Slow file path lookup.
- A timer/debounce incorrectly delaying playback.
- Sound playback launched as a subprocess.
- Audio device suspended.

## 7.3 Correct architecture

Preload and decode the currently assigned volume sound.

Keep a warm, reusable playback route.

Do not spawn a full decoder process for every volume change if the current audio framework supports low-latency playback.

Use the existing Nuxel audio stack.

Do not install a second sound server.

Avoid blocking the volume control or UI thread.

Coalesce slider events intelligently:

- Do not queue a long series of old volume sounds.
- Do not delay playback until the user stops dragging for several seconds.
- Play quickly on actual changes.
- Limit retrigger rate only as necessary.

Target less than approximately 100 ms from input change to audible playback under normal load.

Measure it.

## 7.4 Sound assignment

The volume sound must be selectable through Settings.

Changing the selected sound must update the active sound manager without requiring reboot.

---

# 8. DevMgmt — full graphics acceleration diagnostics

Add a comprehensive graphics acceleration diagnostics section to the DevMgmt app.

It must show which stages of the graphics pipeline are accelerated, partially accelerated or unavailable.

Do not display a single simplistic green "GPU enabled" badge.

## 8.1 Known Nuxel architecture

Previous physical-device work established:

- Mali-G76 MC12.
- Mali kbase.
- Phoc using the Mali graphics stack.
- EGL surfaceless/GLES 3.2.
- Wayland EGL window rendering.
- WebKit GPU rendering.
- WebKit DMA-BUF transport previously blocked.
- Linear linux-dmabuf import in Phoc.
- Framebuffer presentation through `nuxel-wl-fb`.
- Physical output through DECON/AMOLED.
- A CPU copy/scale stage may remain.

Do not hardcode these as current results.

Probe the live device and report current evidence.

## 8.2 Required diagnostic stages

| Stage | What to detect |
|---|---|
| Kernel GPU driver | Mali kbase loaded/active |
| GPU device | `/dev/mali0` and permissions |
| EGL | Vendor, version, renderer |
| GLES | Supported version/extensions |
| Phoc | Actual render backend |
| WebKit | Actual renderer process backend |
| WebKit DMA-BUF | Transport selected |
| DRM discovery | Main DRM device |
| VGEM | Native driver availability |
| GBM | Device initialization and imports |
| linux-dmabuf | Advertised formats/modifiers |
| Phoc import | Actual buffer import results |
| Framebuffer bridge | Runtime health and frames |
| Physical output | Actual final presentation path |
| CPU copy/scale | Whether final stage copies pixels |

## 8.3 Acceleration profiles

Keep distinct profiles:

- GPU rendering.
- GPU-rendered, SHM-presented.
- GPU-rendered, DMA-BUF-presented.
- Fully accelerated.

Use evidence-backed states:

- PASS.
- PARTIAL.
- UNAVAILABLE.
- DEGRADED.
- NOT TESTED.

The actual `fully-accelerated` state must require proof of the final presentation path, not merely Mali rendering.

## 8.4 Evidence

For every stage show:

- Status.
- Driver/backend.
- Last probe time.
- Relevant version.
- Test result.
- Last error.
- Diagnostic details.

Add refresh action.

Do not run expensive stress tests every time DevMgmt opens.

Use lightweight runtime probes and an explicit deeper diagnostic action.

---

# 9. Improve GTK and Flatpak application startup performance

## 9.1 Current issue

Native GTK and Flatpak applications still launch very slowly.

Do not guess the cause.

Profile the actual startup path.

## 9.2 Instrument each stage

Record timestamps for:

- Launcher selection.
- Desktop-entry resolution.
- NuXtore/app registry lookup.
- Process creation.
- D-Bus activation.
- Systemd user manager.
- Portal service.
- Bubblewrap startup.
- User namespace creation.
- Mount namespace setup.
- Flatpak runtime mount.
- Dynamic linker.
- GTK/GLib initialization.
- libadwaita initialization.
- Fontconfig.
- Icon theme.
- Settings/dconf.
- Wayland connection.
- First surface.
- First frame.

Measure both cold and warm launch.

Distinguish:

- Native GTK application.
- Flatpak GTK application.
- Flatpak libadwaita.
- WebKit-backed PWA.
- Electron/Chromium app.

## 9.3 Potential optimization areas

Investigate:

- Synchronous app-list scans.
- Excessive desktop file parsing.
- Redundant icon lookup.
- D-Bus service activation delays.
- Portal activation delays.
- Repeated runtime setup.
- Fontconfig cache generation.
- Icon cache lookup.
- Missing caches.
- Cold page/resource loading.
- Repeated dynamic library mapping.
- CPU/memory pressure.
- Slow filesystem paths.
- Runtime download/repair on launch.
- App startup scripts that block the UI.

Implement only improvements supported by measurements.

## 9.4 Do not compromise sandboxing

Do not disable Bubblewrap.

Do not run Flatpak apps outside their sandbox.

Do not grant blanket host filesystem or device access.

Do not keep all applications permanently resident just to make them appear faster.

Use legitimate prewarming and persistent shared services where appropriate.

Do not create hidden zombie app processes.

## 9.5 Asynchronous launcher

The UI must not wait synchronously for every app to finish launching before remaining interactive.

Display launch progress/status if appropriate.

Ensure the first frame appears as soon as the app is ready.

Do not confuse an app process starting with the actual window becoming usable.

## 9.6 Performance report

Record before/after:

- Cold start.
- Warm start.
- Process creation.
- First window.
- First frame.
- Memory.
- CPU.
- Portal cost.
- Bubblewrap cost.

Use identical test apps and workloads.

---

# 10. Hardware meters — landscape alignment

The desktop hardware meters currently look correct in portrait.

In landscape:

- Text labels are not aligned.
- Meter elements are too tightly positioned.
- Right-side margin is missing.
- Some elements appear too close to the screen edge.

## 10.1 Inspect actual geometry

Use the active logical output dimensions and safe-area information.

Inspect:

- Meter container bounds.
- Text baseline.
- Label width.
- Value width.
- Progress bar width.
- Grid/flex layout.
- Font scaling.
- Device pixel ratio.
- Landscape breakpoints.
- Right margin.
- Safe-area insets.
- Orientation transition events.

## 10.2 Fix

Add a modest right-side margin.

Align labels and values consistently.

Use responsive layout instead of a fixed portrait coordinate system.

Preserve the existing portrait appearance.

Do not shrink every meter or font to compensate for incorrect positioning.

Verify landscape and reverse landscape at actual device resolution.

---

# 11. Gallery navigation

The Back arrow must behave correctly when viewing an image or video preview.

Current desired behavior:

**Back from preview returns to the Gallery main view.**

It must not exit the entire Gallery app.

## 11.1 Image viewer

On Back:

- Close the image viewer surface.
- Restore Gallery main view.
- Restore scroll position.
- Preserve selected item context where appropriate.
- Release image decode/cache references when no longer needed.
- Avoid leaving a transparent viewer overlay.

## 11.2 Video viewer

On Back:

- Stop or pause playback according to Gallery policy.
- Release playback resources.
- Stop audio.
- Remove the video surface.
- Return to Gallery.
- Restore scroll position.
- Prevent playback continuing behind Gallery.

## 11.3 Navigation integration

Use the central Back dispatcher.

The viewer should register an internal Back action while active.

Only when Gallery itself has no further internal navigation should a system Back request close Gallery.

Test images, videos, rapid open/close and orientation changes.

---

# 12. Media Downloader — full yt-dlp integration

The Media Downloader should use `yt-dlp` as its actual extraction/download engine.

Do not create a parallel extractor.

Do not depend on an unrelated browser extension.

## 12.1 Inspect current downloader

Locate the app's current implementation.

Determine:

- Frontend.
- Bridge/API.
- Download service.
- Current downloader backend.
- Output directory.
- Progress reporting.
- Cancellation.
- Dependencies.
- Current URL parsing.
- Error handling.

Preserve existing useful UI and user data.

## 12.2 yt-dlp installation

Verify an ARM64-compatible yt-dlp version.

Inspect:

- Binary/script path.
- Python version if using installed Python package.
- Runtime dependencies.
- FFmpeg.
- FFprobe.
- TLS support.
- Extractor version.
- Update strategy.

Use the maintained package/source appropriate for Nuxel.

Do not install a second conflicting yt-dlp in a random path.

Expose the actual version in diagnostics.

## 12.3 URL workflow

When a user pastes a URL:

1. Trim whitespace.
2. Validate URL structure.
3. Accept supported HTTP/HTTPS URLs.
4. Reject invalid/malformed input.
5. Never pass an untrusted URL through a shell string.
6. Query metadata first.
7. Show title, duration, thumbnail and source.
8. Allow format choice.
9. Start download.
10. Display progress.
11. Allow cancellation.
12. Verify output.
13. Refresh Gallery/media indexing.

Reject unsupported local file URLs and unsafe local-device access.

Do not bypass DRM, paywalls or access controls.

Use content only where downloading is authorized.

## 12.4 MP3 preset

The required user format is MP3.

The current yt-dlp documentation supports:

```bash
yt-dlp -t mp3
```

Use the installed version's built-in preset if available.

The command structure should be equivalent to:

```bash
yt-dlp -t mp3 \
    --cookies-from-browser chrome \
    "<URL>"
```

MP3 extraction requires FFmpeg and FFprobe.

Verify both exist and work.

If the installed yt-dlp version lacks the preset, use its supported explicit audio extraction options and report the compatibility fallback.

## 12.5 MP4 preset

For MP4 use:

```bash
yt-dlp -t mp4 \
    --cookies-from-browser firefox \
    "<URL>"
```

The installed version must be checked for the actual preset behavior.

Do not promise that all sources can be remuxed to MP4 without conversion or that all codecs are compatible with the MP4 container.

Inspect available formats and select a compatible MP4 outcome.

Show when re-encoding is required rather than silently consuming excessive CPU.

## 12.6 Browser cookie selector

Add a visible cookie source selector:

- Nuxel.
- Chrome.
- Firefox.
- None.

The owner expects the selected source to control the downloader command.

### Chrome

Use yt-dlp's native browser cookie option, with the correct profile/keyring handling.

Example:

```bash
yt-dlp -t mp4 \
    --cookies-from-browser chrome \
    "<URL>"
```

### Firefox

Use:

```bash
yt-dlp -t mp3 \
    --cookies-from-browser firefox \
    "<URL>"
```

Support selecting a profile/container if needed.

### Nuxel

Current yt-dlp documentation lists built-in browsers such as:

- Chrome.
- Chromium.
- Firefox.
- Brave.
- Edge.
- Opera.
- Safari.
- Vivaldi.
- Whale.

Nuxel is not listed as a native browser argument.

Do not pass:

```text
--cookies-from-browser nuxel
```

and assume it will work.

Inspect the actual Nuxel browser engine.

If it is WebKitGTK, investigate the actual WebKit cookie manager/profile API.

Implement a Nuxel-specific adapter that exports supported cookies into temporary Netscape-format cookie data if the actual browser API allows it.

Use:

```bash
yt-dlp --cookies <SECURE_TEMPORARY_COOKIE_FILE>
```

for this adapter.

The temporary file must:

- Be stored in a private directory.
- Have restrictive permissions.
- Never be exposed in logs.
- Never be copied into Gallery.
- Be deleted when the download completes or fails.
- Be inaccessible to unrelated applications.

Browser cookies are account credentials. Treat them as secrets.

Do not export or persist all browser cookies unnecessarily.

If WebKit's cookie store cannot safely provide the required data, disable the Nuxel source option and explain the limitation.

Do not fake the selection.

## 12.7 Default cookie behavior

Use the selected browser source.

Nuxel is the preferred default only after its adapter is proven to work.

Otherwise select the most recently selected working source or None.

Do not automatically export cookies without an explicit user choice.

## 12.8 Argument construction

Use a subprocess argument array.

Do not build:

```python
"yt-dlp " + user_url + " " + options
```

Use structured argument construction.

The URL must remain a single argument.

Preserve correct quoting/escaping.

## 12.9 Downloads and progress

Save outputs to the intended Nuxel Downloads directory.

Show:

- Download title.
- Thumbnail.
- Format.
- Destination.
- Progress.
- Speed.
- ETA.
- Status.
- Failure reason.

Support:

- Cancel.
- Retry.
- Open in Gallery.
- Show file location.
- Delete completed download with confirmation.

Prevent duplicate jobs where appropriate.

Do not allow a cancelled job to leave active yt-dlp or FFmpeg processes behind.

---

# 13. Recorder — live waveform

The Audio Recorder app currently records audio but does not display a waveform.

Implement a waveform visualisation based on the actual recorded signal.

## 13.1 Data source

Inspect the actual recording pipeline.

Use the same audio samples or recording file being generated.

Do not generate a fake animated waveform unrelated to the microphone input.

## 13.2 Waveform model

Use a lightweight downsampled representation:

- Peak amplitude per time bucket.
- Optional RMS envelope.
- Time position.
- Duration.
- Recording state.

Do not retain an enormous sample-by-sample array in the UI.

For long recordings, update incremental buckets or process the completed file in chunks.

## 13.3 UI behavior

Show:

- Live waveform while recording, if practical.
- Completed waveform.
- Duration.
- Playback position.
- Playback controls.
- Seek interaction if supported.
- Clear empty/no-recording state.

Respect Nuxel theme and orientation.

Ensure rendering remains smooth on the S10+.

## 13.4 Audio lifecycle

When recording stops:

- Finalize the file.
- Flush data.
- Generate/finalize waveform.
- Save metadata.
- Refresh Gallery.
- Allow immediate playback.

Do not lose the recording if waveform generation fails.

Waveform is secondary metadata; the underlying audio file must remain recoverable.

---

# 14. Appearance Settings — Adwaita and system-wide dark mode

Add an Appearance section to Settings.

The owner wants the ability to select an Adwaita dark appearance or enable a system-wide dark mode so supported GTK and Flatpak menus become dark.

## 14.1 Required choices

At minimum:

- System default.
- Light.
- Dark.

Where supported, provide an Adwaita GTK3 theme selection or an explicit Adwaita Dark option.

Avoid presenting an option that does not actually apply to the installed runtime.

## 14.2 Use supported mechanisms

Inspect the actual Nuxel GTK, GTK3, GTK4 and libadwaita environment.

Libadwaita has its own supported color-scheme mechanism.

Use the system/desktop color-scheme preference and appropriate GSettings/portal integration.

For GTK3, use an installed and available theme.

For Flatpak apps, ensure required theme extensions are present and compatible with the app runtime.

Do not blindly set:

```text
GTK_THEME=Adwaita:dark
```

globally for all applications.

Do not set an empty GTK_THEME environment variable.

This can interfere with GTK/libadwaita appearance behavior.

Inspect existing Flatpak overrides for stale GTK_THEME values.

Do not assume arbitrary environment variables can theme every GTK4/libadwaita application.

## 14.3 System-wide propagation

Apply the chosen preference to:

- Nuxel shell.
- Settings.
- Native GTK3 applications.
- Native GTK4/libadwaita applications.
- Compatible Flatpak GTK applications.
- Compatible portal dialogs.

Use the XDG Settings portal where appropriate.

Respect app-specific forced styles.

Do not promise that an Electron or custom toolkit application will automatically obey GTK dark mode.

Provide truthful status in Settings when an app needs its own theme option.

## 14.4 Persistence and transitions

- Save the preference.
- Apply without reboot.
- Update the shell immediately.
- Notify supported applications through normal settings mechanisms.
- Verify Flatpak portal values.
- Verify persistence across reboot.

Avoid restarting Phoc just to change the theme.

---

# 15. Software app navigation and keyboard

The Software application currently opens with the keyboard visible in some cases.

The user cannot reliably expose the triple navigation buttons or dismiss the keyboard by swiping down.

Fix it using the shared Nuxel keyboard/navigation mechanisms.

## 15.1 Triple buttons

The triple buttons are:

- Back.
- Home.
- Tabs.

In Software:

- They must be accessible when the keyboard is open.
- Swipe up must reveal them.
- They must not be covered by the keyboard.
- Their touch targets must remain correct.
- They must work in all four orientations.

## 15.2 Keyboard dismissal

A downward swipe starting at the keyboard's upper region must dismiss it.

Back must dismiss keyboard before navigating.

Do not create a Software-only competing swipe handler.

Use the central keyboard coordinator.

## 15.3 Regression

Test:

- Open Software.
- Focus search.
- Keyboard appears.
- Swipe up to reveal navigation.
- Tap Tabs.
- Return to Software.
- Swipe down to dismiss keyboard.
- Press Back.
- Open Software again.
- Rotate while keyboard is visible.

No stale keyboard surface or input focus may remain.

---

# 16. Signal — make it work on Nuxel ARM64

Signal must be investigated with current architecture and release information.

Do not assume the older x86_64-only Linux packaging is the entire current story.

## 16.1 Current packaging nuance

Signal's official support page has documented Linux desktop as amd64/x86_64 only.

However, an ARM64 Linux beta build path has also been published.

The agent must verify the current official release channel and the actual binary architecture before selecting an install method.

References:

- Official Signal installation requirements:  
  https://support.signal.org/hc/en-us/articles/360008216551-Installing-Signal

- Official Signal Linux download:  
  https://signal.org/download/linux/

- Signal ARM64 beta packaging/rebuild information:  
  https://github.com/signalflatpak/signal

Do not install an x86_64 binary on the ARM64 device.

Do not build an unofficial x86_64 compatibility layer as a workaround.

## 16.2 Preferred source

Prefer an official Signal-supported ARM64 build if available.

Inspect the current official beta/release channel.

Verify:

- Architecture.
- Release version.
- Package format.
- Signature or checksum.
- Source provenance.
- Update mechanism.
- Runtime dependencies.

If only a community ARM64 Flatpak or rebuild is available:

- Clearly identify it as community maintained.
- Inspect manifest/build recipe.
- Verify the source.
- Verify artifact integrity.
- Verify dependencies.
- Confirm its update mechanism.
- Do not claim it is an official stable Signal package.

## 16.3 Flatpak integration

If a compatible ARM64 Flatpak is available, inspect its current manifest and remote.

Do not assume the ordinary stable Flathub ref contains an ARM64 build just because the app is listed.

Check the actual ref and runtime architecture.

Avoid duplicate old Signal packages.

## 16.4 Wayland and Nuxel integration

Verify:

- Native Wayland or supported XWayland mode.
- HiDPI/scaling.
- Touch usability.
- Keyboard.
- Notifications.
- Audio.
- Deep links.
- System tray behavior, if supported.
- App restart.
- Background lifecycle.
- Correct sandbox permissions.

Do not grant unnecessary host filesystem or D-Bus access.

## 16.5 Pairing

Signal Desktop must be linked to the owner's existing Signal mobile account.

Verify:

- QR code presentation.
- Screen scaling.
- Camera/phone linking workflow.
- Successful pairing.
- Message synchronization.
- App relaunch.

The owner must perform the actual account-linking confirmation.

Do not capture, log or expose:

- QR code contents.
- Messages.
- Private keys.
- Authentication tokens.
- Account secrets.

---

# 17. Central settings and persistence

The new sound, appearance and graphics-diagnostics functionality must integrate with the existing Nuxel Settings architecture.

Do not create disconnected settings files in unrelated locations.

Identify the existing central settings schema and migration mechanism.

For every new setting define:

- Stable key.
- Default.
- Allowed values.
- Validation.
- Persistence location.
- Runtime consumer.
- Migration behavior.
- UI representation.
- Reset/default behavior.

Use a stable user-data location.

Preserve existing user choices.

Do not reset all settings as part of this task.

---

# 18. Performance, memory and storage considerations

The S10+ is a constrained ARM64 mobile device.

Do not introduce heavyweight desktop dependencies unnecessarily.

Evaluate:

- CPU cost.
- Memory use.
- Storage.
- Disk cache growth.
- Concurrent audio pipelines.
- Media downloads.
- Waveform processing.
- GTK theme loading.
- Flatpak runtime setup.
- Signal memory footprint.
- Graphics diagnostic sampling.

Use background tasks for long-running operations.

Never block the desktop event loop while:

- Downloading.
- Installing.
- Scanning media.
- Probing graphics.
- Generating waveforms.
- Reading a large sound folder.

Show progress and allow safe cancellation where appropriate.

---

# 19. Security and privacy

## 19.1 Cookies

Treat browser cookies as credentials.

Do not log cookie contents.

Do not store them in application settings.

Do not expose them through NuXtore or Gallery.

Use short-lived, restrictive temporary files.

Remove them after use.

## 19.2 Media downloads

Use normal authorized downloads.

Do not bypass DRM, paywalls or access controls.

Validate user-provided URLs and avoid shell injection.

## 19.3 Signal

Do not collect message data, account secrets or QR tokens for diagnostics.

## 19.4 Sounds

Validate files before playback.

Do not execute any content from the sound directory.

## 19.5 Flatpak

Preserve normal sandboxing.

Do not add blanket host filesystem or device permissions to improve startup speed or solve appearance problems.

---

# 20. Deep audit — find related issues

After completing the requested changes, perform a broader audit.

Do not stop at the enumerated bullet list.

Inspect related issues across:

- Home and desktop.
- App drawer.
- Dock.
- Quick Settings.
- Settings persistence.
- Sound manager.
- Audio output.
- Clock.
- Notification service.
- Media indexer.
- Gallery.
- Downloader.
- Recorder.
- NuXtore.
- Signal.
- DevMgmt.
- GPU diagnostics.
- GTK.
- Flatpak.
- WebKit.
- Portal backend.
- systemd user services.
- Wayland surfaces.
- Orientation/rotation.
- Keyboard.
- Input method.
- Launch performance.
- App lifecycle.

## 20.1 Findings classification

Classify every additional finding:

- Critical.
- High.
- Medium.
- Low.
- Informational.

For each finding include:

- Reproduction.
- Root cause.
- Evidence.
- Impact.
- Proposed repair.
- Whether it is safe to fix within PWNAGE-81000.

Fix high-confidence related bugs in scope.

Do not expand into an unrelated rewrite or destructive system migration.

Record lower-confidence or unrelated items as a follow-up backlog.

---

# 21. Test and validation plan

Testing must include automated and physical-device verification.

## 21.1 Console indicator

- Local phone usage, no external console: indicator hidden.
- USB SSH Console connected: indicator visible.
- USB SSH Console disconnected: hidden.
- Wi-Fi SSH Console connected: visible.
- Wi-Fi SSH Console disconnected: hidden.
- Agent maintenance SSH only: no false user-console indicator.
- Stale session after reboot: cleared.

## 21.2 Drawer

- Desktop dock absent from drawer.
- Four pinned desktop apps remain on Home.
- Bottom row stable.
- App icons do not flicker.
- Portrait and landscape.
- Keyboard open and closed.
- Repeated open/close.

## 21.3 Sounds

- Sound list populated from supplied assets.
- New file detected.
- Browse custom sound.
- Preview.
- Save assignment.
- Restart.
- Assignment persists.
- Alarm playback.
- Timer playback.
- Volume sound latency measured.
- No delayed/stale audio playback.
- Multiple events handled without uncontrolled overlap.

## 21.4 DevMgmt

- Probe every graphics layer.
- Display partial acceleration honestly.
- Refresh diagnostics.
- Report backend and error.
- No crash when a node is unavailable.

## 21.5 Startup

Measure cold and warm start for:

- GTK native app.
- Flatpak GTK app.
- Flatpak libadwaita app.
- Signal, if installed.

Record improvements and any residual limitation.

## 21.6 Gallery

- Image Back.
- Video Back.
- Restore list position.
- Stop playback.
- Orientation changes.
- No orphaned preview surface.

## 21.7 Downloader

- URL paste.
- Metadata.
- Chrome cookies.
- Firefox cookies.
- Nuxel cookie adapter.
- MP3.
- MP4.
- Download progress.
- Cancel.
- Failed download cleanup.
- Open downloaded file in Gallery.
- Cookie temporary file removal.

## 21.8 Recorder

- Live recording waveform.
- Stop.
- Save.
- Completed waveform.
- Playback.
- Seeking.
- Long recording.
- Storage/reboot persistence.

## 21.9 Appearance

- Light.
- Dark.
- Adwaita GTK3.
- Native GTK.
- libadwaita.
- Flatpak GTK.
- Portal dialogs.
- Reboot persistence.
- Unsupported app reporting.

## 21.10 Software and Signal

- Keyboard open/close.
- Triple navigation reveal.
- Signal launch.
- ARM64 verification.
- Pairing.
- Notifications.
- Touch layout.
- Background/relaunch.

Test all four physical display orientations where appropriate.

---

# 22. Deployment strategy

This is a userspace integration task.

Do not reflash the kernel.

## Stage 1 — Audit

- Connect over Wi-Fi SSH.
- Identify active source.
- Collect baselines.
- Inspect assets.
- Map runtime owners.
- Measure startup and audio latency.

## Stage 2 — Sound manager

- Install sound files.
- Create managed sound directory.
- Implement sound manager.
- Implement Settings.
- Fix Clock.
- Fix volume latency.

Test before proceeding.

## Stage 3 — Desktop and drawer

- Fix live-console indicator.
- Separate dock from drawer.
- Fix flicker.
- Align hardware meters.

Test in all orientations.

## Stage 4 — Media and recorder

- Implement yt-dlp backend.
- Implement cookie-source adapters.
- Implement MP3/MP4 selection.
- Implement progress/cancellation.
- Add waveform.

Test real files.

## Stage 5 — Appearance and application startup

- Implement dark/light settings.
- GTK/libadwaita integration.
- Flatpak theme integration.
- Profile application startup.
- Implement measured improvements.

## Stage 6 — Gallery and Software

- Gallery preview Back behavior.
- Software navigation.
- Keyboard visibility/dismissal.

## Stage 7 — Signal

- Verify current ARM64 distribution path.
- Install appropriate build.
- Verify pairing and desktop integration.

## Stage 8 — DevMgmt and deep audit

- Graphics capability panel.
- Additional source/runtime issues.
- Full regression.

Use incremental deployments.

Avoid restarting the entire desktop unnecessarily.

Keep the SSH connection active.

---

# 23. Regression protection

Do not break existing features.

Preserve:

- Wi-Fi SSH.
- Root access.
- Native Nuxel applications.
- Phoc.
- Mali kbase.
- EGL.
- WebKit host rendering.
- Existing DMA-BUF work.
- Existing framebuffer/DECON output.
- Physical display.
- Touchscreen.
- Fixed display rotation.
- Navigation.
- Existing audio.
- Flatpak sandboxing.
- User data.
- Existing application settings.

`nuxel-wl-fb` remains the sole `/dev/fb0` writer.

Do not add a second display stack.

Do not install a second audio server without demonstrated need.

Do not change kernel or recovery partitions.

---

# 24. Deliverables

Return:

1. Root-cause report for each original problem.
2. Active source/runtime ownership map.
3. Modified source files.
4. New files and service definitions.
5. Updated build/package integration.
6. New sound manager and sound library.
7. Settings appearance/sound UI.
8. Clock and volume audio fixes.
9. DevMgmt graphics diagnostics.
10. GTK/Flatpak startup measurements.
11. Gallery navigation fix.
12. yt-dlp downloader and secure cookie integration.
13. Recorder waveform.
14. Software keyboard/navigation fix.
15. Signal ARM64 compatibility and installation report.
16. App drawer and live-console fixes.
17. Meter layout changes.
18. Additional audit findings.
19. Automated test results.
20. Physical phone acceptance results.
21. Reversible deployment/rollback instructions.

Every deliverable must identify whether it has been tested on:

- Actual S10+ hardware.
- Host development environment.
- Automated/unit tests only.

Do not claim physical verification when none occurred.

---

# 25. Definition of done

### Console

- [ ] Live-console indicator appears only for actual external USB/Wi-Fi console sessions.
- [ ] Ordinary local touchscreen use hides it.
- [ ] Agent maintenance SSH does not create a false console indicator.
- [ ] Console icon underneath remains correct.

### Drawer and meters

- [ ] Four dock icons never appear in app drawer.
- [ ] Bottom row does not flicker.
- [ ] Hardware meter labels align in landscape.
- [ ] Small right-side margin exists.
- [ ] Portrait remains correct.

### Sound manager

- [ ] `./nuxel-sounds` inspected and installed.
- [ ] User `~/Sounds` available.
- [ ] Sound assignments selectable.
- [ ] Sounds autodetected.
- [ ] Browse custom sounds works.
- [ ] Alarm plays.
- [ ] Timer plays.
- [ ] Volume-change sound is immediate.
- [ ] Boot sound can be changed.
- [ ] Future message/notification assignments exist.

### DevMgmt and performance

- [ ] Graphics acceleration stages are accurately reported.
- [ ] Partial acceleration is distinguished from full acceleration.
- [ ] GTK and Flatpak startup are measured.
- [ ] Proven optimizations reduce launch latency.
- [ ] Sandbox remains enabled.

### Media

- [ ] Gallery image/video Back returns to main view.
- [ ] Media Downloader uses yt-dlp.
- [ ] MP3 preset works.
- [ ] MP4 preset works.
- [ ] Browser cookie source is selectable.
- [ ] Chrome/Firefox support works where installed.
- [ ] Nuxel WebKit cookie integration is real or honestly unavailable.
- [ ] Cookie data is protected.

### Recorder and appearance

- [ ] Recorder waveform shows real audio data.
- [ ] Playback and waveform stay synchronized.
- [ ] Appearance Settings exist.
- [ ] Dark/light options work.
- [ ] GTK/libadwaita and Flatpak themes are tested.
- [ ] No broken global theme override.

### Software and Signal

- [ ] Software triple navigation accessible while keyboard is open.
- [ ] Keyboard dismisses via swipe down.
- [ ] Signal ARM64 build is verified.
- [ ] Signal launches.
- [ ] Pairing workflow works.
- [ ] Notifications and app persistence work where supported.

### General

- [ ] Existing Nuxel functionality remains intact.
- [ ] No TWRP flash or kernel rewrite was introduced.
- [ ] All new settings persist.
- [ ] Physical four-orientation regression passes.
- [ ] Deep audit completed.
- [ ] No unresolved critical/high issue is hidden.

---

# 26. Final instruction to the implementation agent

This is a real Nuxel mobile OS integration task.

Do not produce a superficial UI-only implementation.

Do not duplicate the sound manager in individual apps.

Do not let a stale SSH session keep the live-console indicator visible.

Do not leave desktop dock icons underneath the app drawer.

Do not report graphics acceleration as fully enabled unless every stage is proven.

Do not make GTK/Flatpak launches faster by weakening their sandbox.

Do not assume Nuxel is a browser yt-dlp recognizes natively; build a secure, tested cookie adapter if possible.

Do not leak browser cookies.

Do not assume the Signal x86_64 package works on ARM64. Verify the actual official ARM64 build/channel and provenance.

Do not claim dark mode works in every application if that application uses an independent theme system.

The requested improvements should be implemented through shared Nuxel services and settings wherever practical.

Start with Wi-Fi SSH using:

```text
~wicked/.ssh/wicked_wqn_id_rsa
```

Use root console access.

Preserve the current kernel and stable device state.

Measure before and after.

Test on the physical S10+.

**PWNAGE-81000 is complete when Nuxel has a responsive, consistent sound system, reliable mobile application integrations, accurate acceleration diagnostics, proper media workflows, a usable dark appearance, and all the listed desktop features working together as one coherent OS.**
