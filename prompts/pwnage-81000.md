# PWNAGE-81000 — Nuxel Sounds, Media, Applications and Desktop Polish
## Audio manager, Clock, NuXtore downloader, Notes/Recorder, Signal, graphics diagnostics and mobile desktop integration

**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**Platform:** Fedora-based Nuxel ARM64, Phoc/Wayland  
**Deployment:** Wi-Fi SSH, root console  
**SSH key:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Priority:** High  
**TWRP:** Not required for initial work. Do not reflash for these userspace changes.

### 1. Connect to Nuxel

Start with the phone booted normally.

Discover its current Wi-Fi SSH address using the existing Nuxel scripts and connection configuration. Use:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  root@<DISCOVERED_NUXEL_WIFI_HOST>
```

Verify the remote identity, host key and root privileges. Preserve SSH security. Do not expose or copy the private key.

### 2. Fix the live console indicator

The live-console indicator must not remain permanently visible.

Show it only while an actual external Nuxel console session is active:

- USB SSH Console.
- Wi-Fi SSH Console.

The console-type icon underneath already works correctly. Preserve it.

Hide the live-console indicator when the phone is being used locally through its touchscreen and no external console client is connected.

Distinguish actual Tri-Link console sessions from ordinary SSH maintenance sessions, background SSH services and the agent's own administrative connection. Use session ownership/registration, not merely the existence of an SSH process.

When the console disconnects or exits, clear the indicator immediately.

### 3. App drawer dock exclusion and flicker

The four pinned desktop dock applications must never appear inside the app drawer.

Fix the drawer's own application-list rendering and ensure the desktop dock is hidden behind/outside it.

Fix the bottom row flicker. Investigate:

- Duplicate dock rendering.
- Shared layer/overlay ownership.
- CSS stacking and positioning.
- Grid reflow.
- Virtualization/recycling.
- Resize events.
- Animation state.
- Stale app-list updates.

The drawer must remain stable in all four orientations.

### 4. Central sound manager and sounds settings

Inspect the new repository directory:

```text
./nuxel-sounds
```

Preserve and inspect every sound file.

Create a user-accessible sound directory, preferably:

```text
~/Sounds/
```

Copy/install the supplied Nuxel sounds there without losing the original assets. Provide one central sound manager with per-action sound assignments.

Add a Sounds section to Settings with separate choices for:

- Volume change.
- Boot-up.
- Alarm.
- Timer.
- Receiving messages.
- Notifications.
- Other future events.

Message and notification events can be wired later, but their sound assignments must already be configurable.

Requirements:

- Automatically discover newly added compatible sound files.
- Refresh the selectable list when files are added.
- Show filenames and useful metadata.
- Preview each sound.
- Add a Browse button per sound assignment.
- Allow custom files from the filesystem.
- Validate file format and decoder support.
- Preserve choices across reboot.
- Use safe paths and user permissions.
- Avoid duplicating sound files unnecessarily.

### 5. Fix alarm and timer playback

The Clock app currently fails to play:

```text
./assets/nuxel-alarm.mp3
```

Fix both alarm and timer playback.

Resolve assets through the installed resource directory, not the current working directory.

Ensure that:

- The sound loads successfully.
- Playback starts when the alarm/timer actually fires.
- Audio works when Clock is in the background or closed.
- The sound can be dismissed/stopped.
- Repeated alarms do not overlap incorrectly.
- Timer and alarm scheduling persists according to Nuxel's existing behavior.
- The sound uses the central sound-manager assignment.

Test on the physical phone speaker and headphones where available.

### 6. Make volume-change sound instant

The current volume-change sound takes 2–3 seconds to play.

Fix the latency.

Use an already initialized audio output path and preload/decode the assigned sound.

Do not start a new audio server, decoder process or full asset initialization for every slider movement.

Coalesce repeated volume changes safely and avoid playing stale queued sounds.

Target audible playback within approximately 100 ms of the volume-change event under normal load.

Keep sound playback nonblocking.

### 7. DevMgmt graphics acceleration diagnostics

Add a detailed Graphics Acceleration section to DevMgmt.

Detect and report each stage separately:

- Mali kbase driver.
- Mali GPU device access.
- EGL vendor/version.
- GLES support.
- Phoc rendering backend.
- WebKit GPU rendering.
- WebKit DMA-BUF transport.
- DRM main-device discovery.
- DRM/VGEM availability.
- GBM initialization/import.
- linux-dmabuf formats/modifiers.
- Phoc DMA-BUF import.
- Framebuffer bridge.
- `/dev/fb0` presentation.
- CPU copy/scale stage.

Show whether acceleration is:

- Fully verified.
- Partially accelerated.
- Unavailable.
- Degraded.
- Not tested.

Do not report FULLY ACCELERATED merely because Mali is rendering. Keep GPU rendering, DMA-BUF transport and final physical display copy as separate capabilities.

Include useful diagnostics, last error and test evidence.

### 8. GTK and Flatpak application startup performance

Native GTK and Flatpak apps still start too slowly.

Profile cold and warm startup.

Measure:

- Launcher callback.
- Desktop-entry lookup.
- D-Bus activation.
- Portal activation.
- Bubblewrap startup.
- Namespace creation.
- Flatpak runtime preparation.
- Dynamic linker.
- GTK/libadwaita initialization.
- Fontconfig/cache loading.
- Icon/theme loading.
- Wayland connection.
- First frame.

Fix the actual bottlenecks.

Do not disable Flatpak sandboxing, keep every app permanently running, or add arbitrary delays.

Optimize launch scheduling, caches, service activation and unnecessary synchronous discovery.

Compare cold versus warm startup and report measured improvements.

### 9. Hardware meter layout

Portrait layout already looks correct.

In landscape:

- Align meter text and labels properly.
- Add a small right-side margin.
- Prevent the meter from touching the screen edge.
- Respect output safe areas.
- Keep consistent spacing and baselines.
- Preserve portrait geometry.

Use responsive layout based on actual logical output dimensions. Do not introduce hardcoded landscape coordinates.

### 10. Gallery Back behavior

When previewing an image or video, pressing the system Back arrow must return to the Gallery main view, not leave Gallery.

For images:

- Close the preview.
- Restore the previous gallery state and scroll position.

For video:

- Stop/pause playback appropriately.
- Release playback resources.
- Return to the gallery.
- Restore scroll position.

Use the central Back dispatcher and preserve the Gallery app process.

### 11. Media Downloader — yt-dlp backend

Use `yt-dlp` as the actual downloader engine.

When the user pastes a supported URL:

- Validate it.
- Extract metadata.
- Show title, thumbnail, duration and available format.
- Start download with selected cookie source and output format.
- Show real progress.
- Support cancellation.
- Save to the Nuxel Downloads location.
- Refresh Gallery/media discovery when complete.

Default formats:

**MP3:**

```bash
yt-dlp -t mp3 --cookies-from-browser <BROWSER> "<URL>"
```

**MP4:**

```bash
yt-dlp -t mp4 --cookies-from-browser <BROWSER> "<URL>"
```

Use safe subprocess argument arrays, never shell string concatenation.

The current yt-dlp CLI supports the `-t` preset aliases `mp3` and `mp4`. Verify the actual installed version's behavior and dependencies.

MP3 extraction requires FFmpeg/FFprobe.

### Browser cookie selector

Provide a selectable source in the UI:

- Nuxel.
- Chrome.
- Firefox.
- No cookies.

Chrome and Firefox may use yt-dlp's native `--cookies-from-browser` support.

**Nuxel is not a built-in yt-dlp browser identifier.** Implement a tested cookie-export adapter from the actual Nuxel/WebKit browser cookie manager if possible. If unavailable, show the option as unavailable rather than passing `nuxel` to yt-dlp and pretending it works.

For Nuxel custom cookie export:

- Use Netscape cookie format.
- Use a private temporary file.
- Apply restrictive permissions.
- Never log cookie contents.
- Delete the temporary file after the download.
- Never expose cookies in UI diagnostics.
- Preserve user consent and session privacy.

Do not bypass DRM or access controls.

### 12. Audio Recorder waveform

Show a waveform of the recorded audio inside the Recorder app.

Generate waveform data from the actual recorded samples/file.

Requirements:

- Waveform updates during recording if practical.
- Completed recordings show a waveform.
- Playback progress is visible.
- Tapping/seeking works if supported.
- Rendering remains efficient on mobile.
- Long recordings do not require loading the entire file into memory.

Use downsampled peak/RMS data for display, not a huge per-sample UI structure.

### 13. Appearance settings

Add an Appearance section to Settings.

Provide a system-wide dark appearance option using Adwaita/libadwaita-compatible settings.

At minimum:

- System default.
- Light.
- Dark.

Where supported, offer Adwaita Dark as the GTK theme choice.

Apply appearance preferences to:

- Nuxel shell.
- Settings.
- Native GTK apps.
- GTK Flatpak apps.
- Supported libadwaita apps.
- Portal-backed applications.

Use the desktop color-scheme/settings portal and appropriate GTK theme integration.

Do not blindly set `GTK_THEME` globally for every process. Libadwaita has its own color-scheme mechanism, and arbitrary GTK_THEME overrides can make Flatpak GTK/libadwaita applications appear broken.

Verify required Flatpak theme extensions and their availability.

Be honest about non-GTK/Electron/Qt applications that implement their own themes.

### 14. Software app keyboard/navigation

In the Software app:

- Triple navigation buttons must be accessible while the keyboard is open.
- Swiping up must reveal Back/Home/Tabs.
- Swiping down must close the keyboard.
- Back must close the keyboard before navigating or closing the app.

Use the central navigation and keyboard mechanism. Do not add a separate conflicting gesture implementation.

### 15. Signal

Make Signal work on Nuxel ARM64.

Inspect the currently available official Signal Linux ARM64 builds and beta channel, plus Flathub manifests and architecture metadata.

Do not install an x86_64 binary on the ARM64 phone.

Signal's official support page has historically listed Linux amd64, while an ARM64 beta build path has also been published. Verify the current official release/channel and its provenance.

Prefer an official supported ARM64 build. If using a community Flatpak/rebuild, identify it explicitly as community maintained and verify its source, manifest, hashes and update mechanism.

Check:

- ARM64 compatibility.
- Wayland/XWayland.
- WebKit/Electron dependencies.
- Notifications.
- Audio.
- Linking/QR flow.
- Deep links.
- App persistence.
- Updates.

Signal Desktop must be linked to the owner's existing Signal mobile account. Do not capture or log QR codes, messages, keys or private account data.

### 16. Deep audit

After completing the requested changes, perform a broader Nuxel source/runtime audit.

Look for related defects in:

- Sound service.
- App lifecycle.
- Settings persistence.
- Desktop/app drawer.
- Gallery.
- Media indexing.
- NuXtore.
- Recorder.
- Calendar/Clock.
- GTK/Flatpak launch.
- Signal.
- WebKit.
- Wayland/Phoc surfaces.
- Input/keyboard.
- Systemd services.
- Packaging.

Fix additional high-confidence issues that are directly related and safe to resolve within this scope.

Record unrelated or risky discoveries in a separate prioritized findings list. Do not turn the task into an uncontrolled rewrite.

### Mandatory acceptance

- [ ] Live-console indicator appears only during actual USB/Wi-Fi SSH Console sessions.
- [ ] Four desktop dock icons never appear in app drawer.
- [ ] App drawer bottom row no longer flickers.
- [ ] Alarm plays `nuxel-alarm.mp3`.
- [ ] Timer plays its selected sound.
- [ ] Volume sound latency is approximately 100 ms or less.
- [ ] `~/Sounds` contains the supplied sounds.
- [ ] Sound settings support per-action selection and preview.
- [ ] New MP3s are automatically discovered.
- [ ] Custom sound browsing works.
- [ ] DevMgmt shows detailed graphics acceleration stages.
- [ ] GTK and Flatpak cold/warm startup is measured and improved.
- [ ] Hardware meter text alignment is fixed in landscape.
- [ ] Landscape meter has right margin.
- [ ] Gallery preview Back returns to Gallery.
- [ ] Downloader uses yt-dlp.
- [ ] MP3/MP4 formats work.
- [ ] Chrome/Firefox cookies work where installed and supported.
- [ ] Nuxel cookie option is a real tested adapter or honestly unavailable.
- [ ] Recorder shows waveform.
- [ ] Appearance Settings provides dark/light modes.
- [ ] GTK/libadwaita Flatpak appearance is verified.
- [ ] Software app can reveal navigation and dismiss keyboard.
- [ ] Signal works on a verified compatible ARM64 build.
- [ ] Existing Nuxel functionality remains intact.

### Deployment and safety

Use Wi-Fi SSH with `~wicked/.ssh/wicked_wqn_id_rsa`.

Do not reflash the kernel for these userspace features.

Back up all modified files. Preserve user data, cookies, media and app state.

Do not expose browser cookies in logs or diagnostics.

Do not bypass Flatpak sandboxing.

Do not install unverified x86_64 applications.

### Deliverables

- Root-cause report for every requested defect.
- Source and runtime file map.
- Central sound manager and user sound library.
- Updated Settings.
- Downloader integration.
- Recorder waveform.
- Graphics diagnostics.
- GTK/Flatpak performance report.
- Appearance and Signal integration.
- Full four-orientation testing.
- Additional deep-audit findings.
- Reversible deployment and rollback instructions.

**Definition of done:** These features work on the actual S10+ under normal Nuxel usage, not merely in isolated development tests.
