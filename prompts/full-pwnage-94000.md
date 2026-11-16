# full-pwnage-94000.md
# NUXEL FULL PWNAGE 94000
## Doom Audio · Unified Fullscreen Top Bar · Application Startup Performance · Global Adwaita Dark · Back Navigation Lifecycle · Desktop Geometry Restoration

**Project:** Nuxel  
**Target:** Existing Nuxel ARM64 installation, primarily Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Priority:** High  
**Approach:** Deep source analysis → root-cause diagnosis → implementation → automated testing → safe deployment → physical-device verification  
**Required companion:** `pwnage-94000.md`

---

# 0. Mission statement

This is a comprehensive Nuxel usability, performance, and interface reliability engineering task.

Six issues need to be solved as part of one coherent operating-system implementation:

1. Nuxel Doom must launch reliably, have sound enabled by default, and actually produce working audio.
2. Fullscreen applications must use the standard Nuxel desktop top bar rather than an incorrect alternative fullscreen top bar. Its progressive downward opening and single-gesture full closing behavior must be implemented correctly.
3. Native and Flatpak applications still take too long to start. Investigate and improve actual startup performance.
4. Adwaita dark is not consistently respected by all applications. System Monitor is one known example. Establish a reliable system-wide default so supported applications use dark mode automatically.
5. The intermittent invisible surface/input-blocking problem still occurs when leaving an app using the Back arrow in the triple-button navigation.
6. Sometimes leaving an application returns to a vertically displaced desktop: the top bar is outside the visible area, the desktop is shifted upward, and an unexplained gap appears below the four docked icons and above the triple-button navigation.

These issues must be fixed in the actual implementation.

**Do not simply make the symptoms less visible. Find the underlying causes.**

The resulting system should feel like one coherent mobile operating system:

- Doom launches and plays audio.
- Fullscreen applications retain consistent Nuxel system navigation.
- Top-bar gestures are predictable.
- Apps launch promptly.
- GTK applications use a consistent dark appearance.
- Back always returns to an interactive desktop.
- Desktop geometry is restored exactly after an application closes.
- Portrait and landscape behavior remain reliable.

---

# 1. Non-negotiable engineering rules

## 1.1 Investigate before changing

Do not assume that a component is implemented where its filename suggests.

Inspect:

- Repository structure.
- Current project documentation.
- Existing architecture and design specifications.
- Build and deployment scripts.
- Systemd services and user services.
- PWA source and generated assets.
- Wayland compositor configuration.
- Layer-shell surfaces.
- Native bridge and daemon implementations.
- App registry and application launcher.
- GTK configuration.
- Flatpak configuration and overrides.
- Portal services.
- Audio service and routing.
- Input and gesture handling.
- Existing automated tests.
- Runtime state on the actual device.

For each feature, determine the authoritative source of truth and the path by which state travels from input to visible output.

Do not implement a competing subsystem when a suitable existing Nuxel component already exists.

## 1.2 Preserve the existing graphics architecture

Nuxel's graphics and display pipeline must be discovered and preserved.

Historically relevant architecture includes:

- Phoc/Wayland.
- `zwlr_screencopy`.
- `nuxel-wl-fb`.
- A single `/dev/fb0` writer.
- Samsung DECON/AMOLED display output.
- Existing Mali/EGL acceleration where available.

These are investigation starting points, not assumptions that every component is still unchanged.

Do not:

- Introduce a second framebuffer writer.
- Force llvmpipe or software rendering.
- Replace the compositor.
- Blindly set `WLR_*` environment variables.
- Change kernel display drivers.
- Change global display resolution or DPI to compensate for layout bugs.
- Introduce a separate fullscreen UI architecture just to implement the top bar.
- Disable existing graphics acceleration to make a visual bug disappear.

## 1.3 Safe device access

Before any device operation:

1. Discover the current reachable endpoint.
2. Verify SSH host identity.
3. Verify model, hardware, Nuxel installation, build, and effective user.
4. Confirm the intended deployment target.
5. Preserve host-key verification.
6. Never put passwords, tokens, or private keys into scripts or logs.

Do not assume an old IP address remains valid.

Do not flash the bootloader, recovery, kernel, modem, firmware, or other partitions for these userspace changes.

Maintain a recovery route and a known-good previous build.

## 1.4 Honest results

Distinguish between:

- Source-level inspection.
- Automated test results.
- Service/runtime observations.
- Emulator or development-host testing.
- Actual physical-device testing.

Never report an audio test as physically successful based only on a successful process exit code.

Never report a gesture as working because a unit test passed.

Never report performance improvement without measurements.

---

# 2. Phase A — Establish the baseline and map the architecture

Before implementation, produce a private engineering inventory and preserve it in the final report.

## 2.1 Repository and environment inventory

Determine:

- Current Git branch and commit.
- Working-tree status.
- Uncommitted changes.
- Current version/build identifier.
- Active deployment scripts.
- Active configuration files.
- Test commands.
- Device deployment mechanism.
- Current system services.
- Active compositor/session.
- Relevant app and UI components.

Inspect the actual implementation of:

- Home/desktop.
- Status bar.
- Quick Settings.
- Fullscreen app integration.
- Gesture recognizer.
- Bottom triple-button navigation.
- App lifecycle manager.
- Window/surface manager.
- App registry.
- Flatpak integration.
- GTK configuration.
- Audio daemon and audio routing.
- Doom launcher/application package.

Search the repository for likely related components, but do not stop at matching filenames. Follow imports, service calls, IPC, configuration references, and runtime ownership.

## 2.2 Reproduction matrix

Reproduce each problem independently before modifying code.

| ID | Problem | Required baseline |
|---|---|---|
| A | Doom audio | Launch Doom, inspect audio configuration and actual output |
| B | Fullscreen top bar | Open fullscreen app and swipe down |
| C | App startup | Measure native and Flatpak cold/warm starts |
| D | Dark theme | Inspect System Monitor and representative GTK apps |
| E | Invisible surface | Repeatedly leave apps using one Back press |
| F | Desktop displacement | Repeatedly open and close apps in portrait and landscape |

For each issue, record:

- Exact reproduction steps.
- Expected behavior.
- Actual behavior.
- Relevant logs.
- Relevant process and service state.
- Relevant window/surface state.
- Affected source files.
- Whether the failure is deterministic or intermittent.

Do not begin changing several unrelated systems simultaneously. Keep each stage independently testable.

---

# 3. Workstream A — Make Nuxel Doom work properly, with sound enabled by default

## 3.1 Objective

Nuxel Doom must:

- Launch from its intended Nuxel entry point.
- Start reliably.
- Have sound enabled by default.
- Play actual game audio.
- Use the existing Nuxel audio infrastructure.
- Respond to controls correctly.
- Exit without leaving stale surfaces or audio streams.
- Relaunch without requiring manual audio configuration.

The default user experience must not be a silent Doom launch.

## 3.2 Investigate the current Doom implementation

Find the actual Doom engine, package, launcher, data files, configuration, and desktop integration.

Determine:

1. Which Doom engine is used.
2. Which WAD or compatible game data is installed.
3. Whether the intended game data is actually present.
4. How the game is launched.
5. Which working directory it expects.
6. Which environment variables it receives.
7. Whether it uses SDL, OpenAL, PipeWire, ALSA, PulseAudio compatibility, or another audio backend.
8. Whether its configuration disables audio.
9. Whether its audio device selection is wrong.
10. Whether its process is launched with a restricted or incorrect environment.
11. Whether its audio initialization fails silently.
12. Whether the app launcher starts a wrapper script that drops environment variables or changes directories.

Check the real runtime configuration, not just the default configuration shipped in the repository.

## 3.3 Sound must be enabled by default

Establish a reliable default configuration.

Inspect:

- Music enablement.
- Sound-effects enablement.
- Music volume.
- Effects volume.
- Audio device selection.
- Audio backend.
- Sample rate and channel configuration.
- Device availability at launch.
- Audio initialization failures.
- Whether settings are persisted between sessions.

Set sensible nonzero defaults for music and effects.

Do not hardcode an obsolete ALSA device or a device name that only exists on the development machine.

Use the supported Nuxel audio stack and the actual target device's available routes.

If Doom has multiple supported audio backends, select the one that works reliably with the existing system.

Do not bypass Nuxel's sound service merely to make a test tone work.

## 3.4 Startup and audio race conditions

Investigate whether Doom starts before the audio session is ready.

If there is a genuine startup-order problem:

- Use an appropriate readiness check.
- Wait for the relevant audio endpoint to become available.
- Use a bounded timeout.
- Produce useful diagnostics if audio is unavailable.
- Avoid arbitrary fixed sleeps.
- Do not create unnecessary system-wide service dependencies.

Doom should not wait indefinitely for audio.

If audio initialization fails, the game should provide a clear diagnostic and should not crash unnecessarily.

## 3.5 Physical audio verification

Run actual gameplay tests on the S10+.

Required tests:

1. Launch Doom from its Nuxel launcher entry.
2. Confirm the game starts.
3. Confirm menu navigation works.
4. Start a level.
5. Confirm sound effects are audible through the phone speaker.
6. Confirm music is audible if the installed game data supports music.
7. Confirm normal volume controls work.
8. Test an available supported alternative audio route if practical.
9. Exit using the normal navigation path.
10. Confirm audio stops.
11. Relaunch.
12. Confirm sound remains enabled by default.

Record:

- Engine and version.
- WAD/data source.
- Launch command.
- Audio backend.
- Audio configuration.
- Audio device/route.
- Relevant logs.
- Physical test result.

A successful process start does not prove sound works.

A successful audio-device initialization does not prove audible output.

The final report must distinguish these.

## 3.6 Doom regression tests

Add automated tests for:

- Default audio settings.
- Nonzero music/effects volumes.
- Configuration persistence.
- Correct launch environment.
- Valid game data detection.
- Correct working directory.
- Audio backend selection.
- Failure diagnostics.
- Clean process exit.

Do not make automated tests depend on physically audible audio hardware.

---

# 4. Workstream B — Replace the incorrect fullscreen top bar with the standard Nuxel top bar

## 4.1 The problem

When an application is fullscreen and the user swipes down from the top of the screen, a top bar appears.

However, it is the wrong top bar.

Nuxel already has its standard top bar on the desktop. That is the bar that must be used everywhere.

**Remove the incorrect fullscreen-only top bar completely.**

Do not keep two competing implementations and hide one with CSS.

The standard desktop top bar must be the single authoritative Nuxel top-bar implementation.

## 4.2 Investigate both existing top bars

Locate and inspect:

- Standard desktop top bar.
- Fullscreen-specific top bar.
- Quick Settings panel.
- Expanded Quick Settings panel.
- Extended Quick Settings panel.
- Gesture recognition.
- Overlay/layer-shell behavior.
- Surface creation and destruction.
- Fullscreen app state.
- Status information sources.
- Clock, battery, Wi-Fi, sound, connectivity, notification, and remote-session indicators.

Determine:

- Which component owns each top bar.
- Whether the fullscreen bar is a separate DOM tree, PWA, native surface, or compositor layer.
- How the standard bar is shown on desktop.
- Whether status information is duplicated.
- Whether both bars register gestures.
- Whether both bars occupy input regions.
- Whether fullscreen apps use different screen coordinates.
- Whether the standard bar is currently prevented from appearing over fullscreen applications.

The goal is to reuse the existing desktop implementation, not to recreate it.

## 4.3 One authoritative top bar

Implement one authoritative Nuxel top bar.

Requirements:

- The same visual design.
- The same status indicators.
- The same data sources.
- The same clock behavior.
- The same notification count.
- The same connectivity state.
- The same sound state.
- The same accessibility behavior.
- The same responsive layout.
- The same interaction logic.

It must work over:

- Home desktop.
- Native applications.
- GTK applications.
- Flatpak applications.
- Fullscreen applications.
- Portrait orientation.
- Landscape orientation.

The app must remain fullscreen behind the top bar. Do not resize the application viewport unnecessarily just because the panel is temporarily visible.

The top bar must be composited above the application through the existing supported Nuxel/Wayland mechanism.

It must not introduce a new permanently visible window or an input-blocking surface when hidden.

## 4.4 Remove the old fullscreen implementation

Remove the obsolete fullscreen top bar from the actual rendering and event-registration paths.

Specifically:

- Remove its creation/activation path.
- Remove duplicate event listeners.
- Remove duplicate status data subscriptions.
- Remove duplicate gesture registrations.
- Remove obsolete styles and assets if no longer used.
- Remove obsolete configuration references.
- Remove stale IPC handlers if applicable.
- Remove any fallback that silently recreates the old bar.

Do not merely set `display:none`.

If compatibility requires a temporary adapter, it must delegate to the canonical top bar and must not render a separate UI.

## 4.5 Required progressive opening behavior

Implement the following gesture sequence.

<box> </box>

The opening behavior has three levels:

| Gesture | Result |
|---|---|
| First downward swipe | Standard Nuxel top bar |
| Second downward swipe | Expanded Quick Settings |
| Third downward swipe | Extended Quick Settings |

The third level is the most expanded state.

All three levels must use the same Nuxel panel hierarchy and state model.

Do not accidentally interpret a long single swipe as three separate gestures. One physical swipe should advance the panel by no more than one level unless the existing gesture system has an intentional, well-defined alternative.

### Level 0 — Hidden

- Panel completely hidden.
- No visible top bar.
- No stale overlay.
- No invisible surface intercepting input.
- Gesture recognizer remains available.

### Level 1 — Standard top bar

- Show the normal desktop top bar.
- Keep it visually consistent with the desktop.
- Show the same status indicators and state.

### Level 2 — Expanded Quick Settings

- Expand the existing Quick Settings controls.
- Preserve their existing functionality.
- Maintain appropriate spacing and layout.
- Do not create a second Quick Settings implementation.

### Level 3 — Extended Quick Settings

- Show the existing extended controls and additional settings.
- Preserve all working controls.
- Support scrolling if the available display height requires it.
- Do not clip important controls off-screen.

## 4.6 Critical closing behavior: one upward swipe closes everything

This is a strict requirement.

**One upward swipe from any open level must close the entire top-bar panel.**

Examples:

- Level 1 → one upward swipe → Level 0.
- Level 2 → one upward swipe → Level 0.
- Level 3 → one upward swipe → Level 0.

Do not implement:

- Level 3 → Level 2 → Level 1 → Level 0 across three separate upward swipes.
- A partially collapsed panel after a single upward swipe.
- A panel that requires tapping outside to close.
- A panel that remains visible after the gesture finishes.

Opening is progressive. Closing is immediate and complete.

This asymmetry is intentional.

Use a clear state machine, not several unrelated booleans.

A recommended model:

```text
TOPBAR_HIDDEN
TOPBAR_STANDARD
TOPBAR_EXPANDED
TOPBAR_EXTENDED
```

The close operation should be an atomic transition from any visible state to `TOPBAR_HIDDEN`.

## 4.7 Gesture recognition and arbitration

Inspect the actual gesture implementation.

Account for:

- Gesture start position.
- Gesture direction.
- Minimum travel distance.
- Gesture velocity.
- Touch cancellation.
- Multi-touch.
- Vertical scrolling inside Quick Settings.
- Horizontal swipes.
- Application-level touch input.
- Display orientation.
- System navigation gestures.
- Input regions.
- Existing fullscreen app touch behavior.

Do not let a scroll gesture inside an expanded panel accidentally advance the panel to the next level.

Do not let an app consume the initial system edge gesture when the gesture starts inside the reserved Nuxel system gesture region.

Do not globally intercept all touch events.

Only the relevant system edge gesture should be handled by the system.

Ensure the top bar does not steal unrelated touch input when hidden.

## 4.8 Landscape swipe area improvements

Landscape currently makes the top and bottom gesture areas too difficult to use.

Increase the swipe-up activation area for:

1. Hiding the top bar.
2. Activating the bottom triple-button navigation controls.

This must be done in a deliberate, measurable way.

Investigate:

- Existing edge gesture region dimensions.
- Portrait vs landscape coordinate transforms.
- Logical vs physical pixels.
- Scaling and device density.
- Touch coordinates received from Wayland.
- Whether the active region is clipped.
- Whether the top bar surface changes its input region.
- Whether the bottom navigation surface has a smaller touch region than its visible area.

### Top gesture

When the top bar is visible in landscape, a slightly larger swipe-up region must reliably close it.

### Bottom navigation gesture

Increase the relevant landscape bottom interaction area so the triple-button navigation remains easy to activate.

Preserve the actual button layout and visual size unless a separate, evidence-based issue requires changing them.

Do not cause the bottom navigation area to intercept normal application interactions excessively.

### Acceptance

Test at least:

- Portrait.
- Landscape left.
- Landscape right, if supported.
- Fullscreen app.
- Non-fullscreen app.
- Top bar visible at each of its three levels.
- Top bar hidden.
- Quick Settings scroll interaction.
- Bottom navigation interaction.

Measure the final activation region in the correct coordinate system.

## 4.9 Top-bar regression tests

Implement tests for:

- Correct top-bar component selected in fullscreen.
- No obsolete fullscreen bar rendered.
- Exactly one authoritative status bar.
- No duplicate gesture listener.
- First downward gesture opens Level 1.
- Second opens Level 2.
- Third opens Level 3.
- One upward gesture from each open level closes everything.
- No partial collapse.
- Scrolling inside Quick Settings does not trigger expansion.
- Touch cancellation does not leave the panel stuck.
- Fullscreen application remains fullscreen behind the panel.
- Hidden panel has no active input-blocking region.
- Landscape hit regions are correctly calculated.
- Desktop behavior remains unchanged.

---

# 5. Workstream C — Improve native and Flatpak application startup performance

## 5.1 Problem

Native and Flatpak applications still start too slowly.

Do not assume the Flatpak sandbox itself is the only cause.

Investigate the entire launch path from the user tapping an icon to the first usable application frame.

The goal is to make Nuxel feel responsive without sacrificing sandbox security or application stability.

## 5.2 Build a real launch pipeline map

Trace the actual launch sequence:

```text
User taps app icon
        |
        v
Nuxel launcher / app registry
        |
        v
Launch request / IPC
        |
        v
Application classification
        |
        v
Native or Flatpak launch path
        |
        v
Environment and desktop integration
        |
        v
Process creation
        |
        v
Portal / D-Bus / service activation
        |
        v
Toolkit initialization
        |
        v
Window / Wayland surface creation
        |
        v
First rendered frame
        |
        v
Application ready for interaction
```

This is a conceptual trace. Discover the actual implementation and replace the diagram with the real one in the report.

Identify where time is spent.

## 5.3 Establish reproducible baseline measurements

Measure at least:

- One small native application.
- One medium native application.
- One heavier native application.
- One small Flatpak application.
- One medium Flatpak application.
- One heavier Flatpak application.

Choose representative applications actually installed on Nuxel.

Measure:

| Metric | Meaning |
|---|---|
| T0 | User launch request |
| T1 | Launch request accepted |
| T2 | Process creation |
| T3 | First application surface |
| T4 | First rendered frame |
| T5 | Application ready for interaction |

Derive:

- Request-to-process time.
- Process-to-surface time.
- Surface-to-first-frame time.
- Total launch-to-interaction time.

Separate:

- Cold launch.
- Warm launch.
- First launch after boot.
- Subsequent launches.
- Launch after app has been closed.
- Launch when relevant services are already active.

Use a monotonic clock and reliable instrumentation.

Do not confuse process creation with application readiness.

## 5.4 Investigate likely bottlenecks

Inspect the actual runtime for:

### Nuxel launcher

- Duplicate app discovery.
- Repeated `.desktop` parsing.
- Repeated Flatpak metadata scans.
- Synchronous filesystem operations.
- Blocking icon loading.
- Blocking app registry lookups.
- Unnecessary IPC round trips.
- Expensive UI updates.
- Repeated environment construction.
- Redundant app classification.

### Flatpak

- Repeated metadata resolution.
- Runtime discovery.
- Mount and sandbox setup.
- D-Bus activation.
- Portal activation.
- Permission checks.
- Filesystem and environment configuration.
- Application startup scripts.
- Runtime availability.
- Repeated metadata queries.

### Native apps

- Wrapper scripts.
- Excessive shell subprocesses.
- Repeated dependency checks.
- Blocking environment preparation.
- Unnecessary service activation.
- Desktop-entry parsing.
- Startup configuration.

### Shared infrastructure

- D-Bus responsiveness.
- systemd user services.
- Portal startup.
- GTK initialization.
- Wayland surface creation.
- Icon theme lookup.
- Font cache.
- Storage I/O.
- Memory pressure.
- CPU scheduling.
- Cold page-cache effects.
- Existing service startup dependencies.

Use logs, profiling, process tracing, and measurements to identify real bottlenecks.

Do not guess based on generic Linux desktop behavior.

## 5.5 Implement evidence-based improvements

Possible improvements, only when supported by measurements:

- Cache application registry metadata.
- Cache resolved desktop-entry IDs.
- Avoid repeated Flatpak metadata scans.
- Precompute launch metadata.
- Remove redundant wrapper processes.
- Eliminate unnecessary synchronous UI work.
- Defer nonessential icon loading.
- Improve asynchronous launch handling.
- Avoid blocking the launcher while a process initializes.
- Reuse existing ready system services.
- Correct unnecessary systemd dependencies.
- Reduce avoidable D-Bus round trips.
- Avoid redundant portal initialization.
- Improve first-frame presentation.

Do not preload every application blindly.

Do not start every Flatpak runtime at boot.

Do not keep every application resident just to improve a benchmark.

Do not increase memory pressure beyond what the device can support.

Do not disable Flatpak sandboxing.

Do not grant unnecessary filesystem, device, or session permissions.

## 5.6 First-frame experience

The launcher must remain responsive while an application starts.

If a real startup delay remains:

- Show a lightweight, consistent launching state.
- Do not block system navigation.
- Do not show an incorrect application icon or duplicate window.
- Remove the launch indicator when the actual application surface is ready.
- Handle launch failures cleanly.
- Prevent duplicate launches from repeated taps unless multiple instances are intentional.

A launch indicator is not a substitute for performance improvement.

## 5.7 Performance acceptance

After implementation, repeat the same benchmark conditions.

Report:

- Per-app cold launch time.
- Per-app warm launch time.
- First surface time.
- First frame time.
- Ready-for-interaction time.
- CPU usage where relevant.
- Memory impact.
- Any trade-offs.

Show before/after values.

Do not invent a universal percentage target before measuring the baseline. Set realistic targets based on actual bottlenecks and hardware limitations.

A regression in one class of apps must not be hidden by an average improvement elsewhere.

---

# 6. Workstream D — Make Adwaita dark the reliable default for supported applications

## 6.1 Problem

Nuxel is intended to use Adwaita dark by default, but not all apps respect it.

System Monitor is one observed example that still appears light.

The user should not have to open individual applications and configure their themes.

Establish a reliable system-wide default for applications that support GTK and Adwaita theming.

## 6.2 Discover the current theme implementation

Inspect:

- `/etc/gtk-3.0/settings.ini`, if present.
- User GTK 3 configuration.
- GTK 4 configuration.
- `gsettings`.
- `org.gnome.desktop.interface`.
- `color-scheme`.
- `gtk-theme`.
- `Adwaita`.
- `Adwaita-dark`.
- `XDG_CONFIG_HOME`.
- `XDG_DATA_DIRS`.
- Session environment variables.
- Flatpak application environment.
- Flatpak overrides.
- XDG Desktop Portal.
- Portal settings implementation.
- D-Bus activation environment.
- Application-specific overrides.
- Installed GTK themes and icon themes.

Find the actual source of truth.

Do not add multiple conflicting theme mechanisms without understanding precedence.

## 6.3 Establish the desired default

For supported GTK applications, the default appearance must be Adwaita dark.

Use the appropriate supported mechanism for the installed GTK versions.

Investigate the correct distinction between:

- GTK 3 theme selection.
- GTK 4 color-scheme preference.
- GTK 4 Adwaita behavior.
- GNOME desktop interface color-scheme.
- XDG portal appearance preference.
- Flatpak sandbox environment.

Do not assume a GTK 3 setting automatically controls GTK 4.

Do not assume that changing a host environment variable automatically reaches Flatpak applications.

Do not assume every application is a GTK application.

## 6.4 GTK 3

Verify:

- GTK 3 theme preference.
- Theme availability.
- Theme lookup paths.
- User/system configuration precedence.
- Host defaults.
- Flatpak visibility of relevant settings.

Ensure GTK 3 applications select the intended dark appearance by default.

Do not copy random themes into multiple directories to mask a configuration error.

## 6.5 GTK 4 and libadwaita

Verify:

- GTK 4 color scheme.
- Adwaita dark preference.
- libadwaita behavior.
- XDG portal color-scheme preference.
- Session environment.
- User settings.
- Flatpak environment propagation.

Use the supported mechanism appropriate to the actual installed GTK/libadwaita versions.

Do not force unsupported theme overrides onto libadwaita applications.

Some libadwaita applications intentionally follow the system color-scheme preference rather than arbitrary GTK theme names. Respect that behavior.

## 6.6 Flatpak applications

This is a critical part of the workstream.

Inspect the actual Flatpak environment of installed applications.

Verify:

- GTK configuration is visible where expected.
- Theme assets are available where required.
- Color-scheme settings propagate into the sandbox.
- Portals expose the intended appearance preference.
- User overrides do not conflict.
- Application-specific overrides are not forcing light mode.
- The correct theme/runtime extension is available if needed.

Use the least invasive system-wide method that works.

Avoid setting one-off overrides for every installed application as the primary solution.

Do not blindly apply global Flatpak overrides that grant additional permissions or weaken sandboxing.

If an application has an explicit user override, distinguish it from the default behavior. Preserve intentional user customization where possible.

## 6.7 Test applications

At minimum, test representative applications from the actual installation:

- GNOME System Monitor or the installed equivalent.
- One GTK 3 application.
- One GTK 4 application.
- One libadwaita application.
- One Flatpak GTK application.
- One Flatpak libadwaita application.
- One native GTK application.

For each, report:

| Application | Packaging | Toolkit | Expected | Actual |
|---|---|---|---|---|
| System Monitor | Actual | Actual | Dark | Verified result |
| GTK 3 app | Actual | GTK 3 | Dark | Verified result |
| GTK 4 app | Actual | GTK 4 | Dark | Verified result |
| libadwaita app | Actual | libadwaita | Dark | Verified result |
| Flatpak GTK app | Flatpak | Actual | Dark | Verified result |
| Flatpak libadwaita app | Flatpak | Actual | Dark | Verified result |

Use actual installed applications, not invented test names.

## 6.8 Theme persistence

Verify:

- Reboot persistence.
- New application launches.
- Existing application behavior after restart.
- Flatpak app behavior after restart.
- New user session behavior if applicable.
- Configuration precedence.
- No need to configure each app manually.

Document exceptions where an application does not support the system preference or deliberately overrides it.

The objective is a reliable default, not a false claim that every application on Linux supports Adwaita.

## 6.9 Dark theme regression tests

Add tests for:

- System-level color-scheme default.
- GTK 3 configuration.
- GTK 4 color-scheme.
- Portal preference.
- Flatpak visibility.
- Conflicting override detection.
- Reboot/session persistence where automated testing permits.

Do not use screenshots alone as proof of the configuration source. Combine visual verification with environment and configuration inspection.

---

# 7. Workstream E — Fix the invisible surface/input-blocking issue when leaving applications

## 7.1 Problem

Sometimes, when leaving an application with the Back arrow in the bottom triple-button navigation, the user returns to the desktop but an invisible surface or overlay remains.

The desktop looks present, but it is not fully interactive.

For example, the user may be unable to swipe open the application drawer until a long Back press triggers foreground application termination.

This is a serious lifecycle/input-management issue.

**A normal Back press must reliably restore a fully interactive desktop.**

## 7.2 Do not treat long-Back termination as the fix

The long-Back foreground kill is a separate emergency/termination action.

Do not repurpose it to hide the underlying bug.

The short Back action must work correctly.

Preserve the distinction between:

- Application internal navigation.
- Dismissing an app-owned dialog or modal.
- Closing an app-owned transient surface.
- Returning from the application to the Nuxel desktop.
- Explicitly terminating an application through the long-Back action.

## 7.3 Reproduce and classify

Test:

- Native applications.
- GTK applications.
- Flatpak applications.
- Browser/PWA applications.
- Fullscreen applications.
- Applications with dialogs.
- Applications with menus.
- Applications with multiple windows.
- Applications with internal navigation history.

For each case:

1. Launch application.
2. Wait for a stable visible surface.
3. Press Back once.
4. Observe the visible desktop.
5. Immediately test Home and app drawer interaction.
6. Test top-edge gestures.
7. Test bottom navigation.
8. Repeat.
9. Compare with long-Back termination.

Record whether the failure is associated with a particular app type or surface lifecycle.

## 7.4 Trace the full lifecycle

Inspect:

- Wayland surface creation.
- Wayland surface destruction.
- Parent/child surface relationships.
- Subsurfaces.
- XDG toplevel lifecycle.
- Popup surfaces.
- Layer-shell surfaces.
- Input regions.
- Keyboard focus.
- Pointer focus.
- Touch focus.
- Seat state.
- Compositor activation.
- App window state.
- PWA visibility.
- DOM overlays.
- Native bridge events.
- IPC messages.
- Application process state.
- Foreground app registry.
- Navigation manager.
- Gesture ownership.

Find the actual surface or input region that survives when the issue occurs.

Determine whether the problem is:

- A stale mapped surface.
- An invisible but active overlay.
- An input region that was never cleared.
- A stale touch grab.
- A stale keyboard/pointer focus.
- An app lifecycle transition that did not complete.
- A race between Home restoration and surface teardown.
- A mismatched window identifier.
- A stale PWA overlay.
- A compositor activation issue.
- A duplicate input listener.
- A failure to receive or process an acknowledgment.

Do not guess.

## 7.5 Define a canonical lifecycle

Inspect the existing lifecycle architecture and normalize it if necessary.

A possible state model:

```text
HOME_ACTIVE
APP_LAUNCHING
APP_ACTIVE
APP_MODAL_ACTIVE
APP_MINIMIZING
APP_CLOSING
HOME_RESTORING
LOCKED
UNKNOWN
```

Do not introduce duplicate state machines if an existing authoritative model can be repaired.

Every transition must have a clear owner.

A normal Back press should:

1. Determine whether the foreground app can handle Back internally.
2. If an app-owned modal or navigation level can consume Back, let it do so.
3. Otherwise initiate the correct return-to-home transition.
4. Restore the desktop.
5. Release stale app-owned input and surface state.
6. Restore Nuxel system gesture readiness.
7. Confirm the transition has completed.

Do not terminate the application unless the established behavior explicitly requires it.

## 7.6 Cleanup must be deterministic and idempotent

The cleanup path must safely handle:

- Surface already destroyed.
- Application process already exited.
- Duplicate close event.
- Delayed IPC response.
- Interrupted transition.
- Application crash.
- Focus change during transition.
- Orientation change.
- Screen lock during transition.
- Rapid repeated Back presses.

Use the actual event and lifecycle acknowledgments available from the compositor and app manager.

Do not use arbitrary sleeps to wait for a surface to disappear.

Do not blindly destroy every surface associated with an application if child surfaces or shared system UI belong to another owner.

Do not globally clear all touch focus or all compositor surfaces.

Only clean up the relevant app-owned state.

## 7.7 Home restoration

The desktop must be fully ready when the Back transition reports completion.

Verify:

- Home surface mapped.
- Home surface visible.
- Correct stacking order.
- Correct input region.
- Home gestures registered exactly once.
- No app overlay intercepting touch.
- No stale touch grab.
- Correct focus state.
- Correct foreground application state.
- No duplicate desktop instance.
- No stale transition flag.

The user must be able to immediately:

- Swipe to open the app drawer.
- Tap docked icons.
- Use Home.
- Use Tabs.
- Open Quick Settings.
- Launch another application.

## 7.8 Diagnostics

Add structured diagnostics for lifecycle transitions.

Useful fields include:

- Monotonic timestamp.
- Transition ID.
- App ID.
- Surface ID.
- Parent surface ID where available.
- Previous lifecycle state.
- Next lifecycle state.
- Input-region owner.
- Focus owner.
- Cleanup action.
- Acknowledgment/result.
- Failure reason.

Avoid logging sensitive application content.

Make it possible to distinguish a real lifecycle cleanup failure from a normal application-owned modal.

## 7.9 Regression testing

Automate:

- Single Back at app root.
- Back inside app navigation.
- Back with app modal open.
- Back with popup open.
- Back during launch.
- Back during close.
- Duplicate Back.
- Application crash.
- Surface destruction before close acknowledgment.
- Repeated open/close cycles.
- Return to interactive Home.
- Immediate app drawer swipe after Back.

Perform at least 20 repeated physical-device cycles across representative app types.

The exact result must be reported.

---

# 8. Workstream F — Fix desktop vertical displacement and viewport restoration

## 8.1 Problem

Sometimes leaving an app returns to the desktop in an incorrect vertical position.

Observed symptoms:

- Desktop content is shifted upward.
- Top bar is partially or completely outside the visible screen.
- Four docked icons appear in the lower portion.
- An unexplained blank strip appears below those icons.
- Triple-button navigation remains below the blank strip.
- Desktop does not return to its normal full-screen layout.

This may be related to the invisible surface problem, but do not assume they have the same root cause.

Investigate both independently and then determine whether they share a lifecycle or geometry defect.

## 8.2 Determine the actual coordinate systems

Inspect:

- Physical display resolution.
- Logical Wayland output dimensions.
- Device scale factor.
- Rotation transform.
- Viewport dimensions.
- Browser/PWA viewport.
- Safe areas.
- Top system bar dimensions.
- Bottom navigation dimensions.
- Dock dimensions.
- Application surface dimensions.
- Compositor layer arrangement.
- Window position.
- Transform/translation state.
- Scroll position.
- CSS viewport units.
- Orientation event handling.
- Fullscreen transitions.

Determine whether the offset comes from:

1. Compositor layer position.
2. Wayland surface geometry.
3. PWA viewport resizing.
4. CSS transform.
5. A stale scroll position.
6. A duplicated inset/safe-area calculation.
7. A stale orientation transform.
8. A bottom navigation reservation applied twice.
9. Incorrect fullscreen restoration.
10. A transition animation that never resets.
11. A stale window/surface size.
12. Incorrect top-bar visibility state.

Do not change display resolution or global DPI to hide a coordinate error.

## 8.3 Establish one geometry authority

Identify which component owns the canonical desktop viewport and system insets.

Avoid independently calculating top and bottom reservations in several layers.

If geometry is currently duplicated, establish one consistent source of truth.

The desktop layout must account for:

- Display bounds.
- Top system bar.
- Main desktop area.
- Dock.
- Bottom triple-button navigation.

Avoid double-applying system insets.

Ensure that fullscreen application content and desktop content use their appropriate viewports without corrupting one another.

## 8.4 Restore geometry on every transition

When returning to Home, ensure:

- Desktop position resets correctly.
- Top bar is visible in its normal position.
- Desktop starts at the correct vertical origin.
- Dock is in its normal position.
- Four docked icons remain in their intended position.
- No extra blank strip appears.
- Bottom navigation remains correctly aligned.
- Main desktop area uses the full intended height.
- Previous app fullscreen geometry does not leak into Home.

The restoration must work regardless of whether the previous application was fullscreen.

## 8.5 Check animation and transform cleanup

Inspect every relevant transition animation.

Check for:

- Incomplete CSS transitions.
- Stale `transform: translateY(...)`.
- Stale offsets.
- Animation interruption.
- Transition classes not removed.
- Scroll lock not restored.
- Viewport dimensions cached before rotation.
- Safe-area calculations applied more than once.
- Hidden elements retaining layout space.
- Dock and navigation reservations being applied simultaneously by two components.

A visual reset that only runs after a delay is not acceptable unless there is a real asynchronous dependency and a verified completion event.

Prefer deterministic state reset and event-driven geometry restoration.

## 8.6 Portrait and landscape

Test:

- Portrait desktop → native app → Back.
- Portrait desktop → Flatpak app → Back.
- Portrait desktop → fullscreen app → Back.
- Landscape desktop → native app → Back.
- Landscape desktop → Flatpak app → Back.
- Landscape desktop → fullscreen app → Back.
- Rotate while app is open, then Back.
- Rotate immediately after Back.
- Open Quick Settings, close it, then Back.
- Open/close repeated apps.

Take screenshots or capture measurable geometry at consistent stages.

Compare desktop bounds before and after application transitions.

## 8.7 Geometry regression tests

Add automated tests for:

- Desktop top origin.
- Top bar visibility.
- Dock bounds.
- Four docked icon positions.
- Bottom navigation bounds.
- Main desktop viewport height.
- No unexplained vertical gap.
- No stale transforms.
- No duplicate inset.
- Orientation restoration.
- Fullscreen exit restoration.
- Repeated app transitions.

Where visual tests are possible, use stable reference captures and tolerant bounds rather than brittle exact-pixel matching.

---

# 9. Workstream G — Cross-feature integration

The six workstreams must work together.

Do not consider the task complete just because each feature passes independently.

## 9.1 Fullscreen and system UI

Test:

1. Launch Doom.
2. Enter gameplay.
3. Swipe down once.
4. Confirm standard Nuxel top bar.
5. Swipe down again.
6. Confirm expanded Quick Settings.
7. Swipe down again.
8. Confirm extended Quick Settings.
9. Swipe up once.
10. Confirm the entire panel disappears.
11. Confirm Doom is still running and responsive.
12. Confirm audio continues.
13. Exit Doom using normal Back behavior.
14. Confirm desktop geometry is correct.

## 9.2 Back and geometry

Test app transitions with:

- Standard top bar hidden.
- Standard top bar visible.
- Expanded Quick Settings.
- Extended Quick Settings.
- Landscape orientation.
- App modal open.
- App fullscreen.
- App launch in progress.

No stale top bar, surface, transform, input region, or panel state may remain.

## 9.3 Dark theme and startup

Verify that:

- GTK apps launched from the Nuxel launcher receive the correct theme.
- Flatpak apps launched from the Nuxel launcher receive the correct theme.
- Applications started after a fresh boot still use dark mode.
- Faster launch changes do not bypass the correct environment or portal settings.

## 9.4 Performance and navigation

Verify:

- Launcher remains interactive during application startup.
- Top bar remains responsive during application startup.
- Back remains responsive.
- App close does not block Home restoration.
- Doom audio is not interrupted by unrelated UI activity.
- No additional permanent services create unnecessary boot delay.

---

# 10. Workstream H — Testing strategy

## 10.1 Unit tests

Add or update tests for:

- Doom launch configuration.
- Doom sound defaults.
- Top-bar state machine.
- Top-bar gesture transitions.
- Single-swipe close.
- Landscape gesture regions.
- Application launch metadata.
- Startup timing instrumentation.
- GTK theme defaults.
- Flatpak theme propagation.
- App lifecycle transitions.
- Surface cleanup.
- Input-region restoration.
- Desktop geometry restoration.

## 10.2 Integration tests

Test interactions between:

- Launcher and native apps.
- Launcher and Flatpak apps.
- Launcher and fullscreen apps.
- Top bar and Quick Settings.
- Top bar and app input.
- Back and application lifecycle.
- Back and desktop geometry.
- GTK settings and Flatpak sandbox.
- Doom and Nuxel audio.

## 10.3 Regression tests

Preserve existing functionality.

At minimum verify:

- Home.
- Back.
- Tabs.
- App drawer.
- Docked icons.
- Quick Settings controls.
- Sound mode.
- Battery and connectivity indicators.
- Lock screen.
- Existing audio playback.
- Bluetooth.
- Wi-Fi.
- Existing application permissions.
- App launch and exit.

Do not allow one fix to break a previously working system component.

## 10.4 Physical-device test matrix

<text> </text>

| Test | Portrait | Landscape |
|---|---|---|
| Standard top bar | Required | Required |
| Progressive panel opening | Required | Required |
| One-swipe full close | Required | Required |
| Fullscreen application | Required | Required |
| Bottom navigation hit area | Required | Required |
| Single Back restoration | Required | Required |
| Desktop geometry | Required | Required |
| Native app launch | Required | Required |
| Flatpak app launch | Required | Required |
| Doom gameplay/audio | Required where supported | Required where supported |

Record actual results. If a test cannot be performed, say why.

---

# 11. Workstream I — Performance and resource safety

Measure the impact of the changes.

Do not optimize one metric at the expense of overall system responsiveness.

Track:

- Idle CPU.
- Idle memory.
- Launcher memory.
- Launcher CPU during app discovery.
- Top-bar opening/closing latency.
- Quick Settings rendering.
- App startup latency.
- Doom launch latency.
- Doom audio startup.
- Back-to-Home latency.
- Desktop restoration latency.
- Number of active surfaces.
- Number of active gesture listeners.
- Number of app processes.
- Relevant service startup overhead.

Do not introduce permanent high-frequency polling.

Prefer event-driven state updates.

Do not create a large number of background processes or preload every application.

The S10+ has constrained resources. Avoid unnecessary memory retention and expensive visual effects.

The objective is a responsive, stable system.

---

# 12. Workstream J — Safe implementation and deployment

## 12.1 Before editing

- Confirm the Git working tree.
- Preserve user modifications.
- Create a clearly identifiable working branch or checkpoint.
- Record the current commit.
- Record the current device build.
- Preserve a known-good deployment path.

Do not discard unrelated user changes.

## 12.2 Implementation sequence

Recommended sequence:

1. Architecture inventory and baseline.
2. Doom audio investigation and fix.
3. Canonical top-bar integration.
4. Gesture state machine and landscape hit areas.
5. GTK/Flatpak dark-theme defaults.
6. Startup performance instrumentation and fixes.
7. Back lifecycle and invisible surface fix.
8. Desktop geometry restoration.
9. Cross-feature regression.
10. Deployment and physical verification.

If the investigation proves that two issues share one underlying cause, fix the common cause while keeping separate regression coverage.

## 12.3 Deployment safety

Before deploying:

- Build all changed components.
- Run relevant tests.
- Validate configuration.
- Check service definitions.
- Check file ownership and permissions.
- Confirm no unintended changes to boot-critical files.
- Confirm the device target.
- Preserve rollback artifacts.

Deploy only the required userspace changes.

Do not flash kernel or firmware partitions.

After deployment:

- Verify active build identity.
- Verify service state.
- Verify the expected files are active.
- Verify logs.
- Perform physical tests.

Do not report success solely because deployment returned exit code zero.

## 12.4 Rollback

Provide a documented rollback for each independently deployable subsystem where practical.

The rollback must cover:

- Top-bar component and gesture changes.
- Theme defaults and Flatpak configuration.
- Application launcher/startup changes.
- Lifecycle and surface cleanup changes.
- Desktop geometry changes.
- Doom configuration and launcher changes.

Avoid a rollback procedure that requires a complete OS reinstall for a userspace regression.

---

# 13. Workstream K — Documentation and final report

Create:

`REPORT-PWNAGE-94000.md`

The report must contain:

## 13.1 Executive summary

State which issues were fixed, which were not, and the overall outcome.

## 13.2 Root-cause analysis

For all six workstreams:

- Original behavior.
- Reproduction steps.
- Root cause.
- Evidence.
- Affected components.
- Exact files changed.
- Final behavior.

## 13.3 Doom report

Include:

- Engine.
- Version.
- Game data.
- Launch path.
- Audio backend.
- Default configuration.
- Physical speaker test.
- Music test.
- Effects test.
- Relaunch test.
- Remaining limitations.

## 13.4 Top-bar report

Include:

- Previous standard top-bar implementation.
- Previous fullscreen-only implementation.
- Which implementation was removed.
- Canonical component.
- State machine.
- Gesture behavior.
- Single-swipe close implementation.
- Landscape hit-region dimensions.
- Portrait and landscape test results.

## 13.5 Performance report

Include actual before/after launch measurements for each tested native and Flatpak application.

Explain the real bottlenecks and which optimizations addressed them.

Include memory/CPU trade-offs.

## 13.6 Dark-theme report

Include:

- GTK 3 configuration.
- GTK 4 configuration.
- libadwaita behavior.
- Portal settings.
- Flatpak behavior.
- System Monitor result.
- Representative application matrix.
- Reboot persistence.

Clearly list applications that do not support the intended theme preference.

## 13.7 Lifecycle report

Include:

- Exact invisible surface/input-blocking root cause.
- Surface and focus lifecycle.
- Back behavior before and after.
- Cleanup mechanism.
- Diagnostics added.
- Repeated physical-device cycle results.

## 13.8 Geometry report

Include:

- Original incorrect geometry.
- Actual root cause.
- Coordinate system findings.
- Canonical geometry owner.
- Corrected desktop bounds.
- Portrait and landscape test results.
- Evidence that the top bar, dock, and bottom navigation return to their correct positions.

## 13.9 Test report

List:

- Commands executed.
- Automated tests passed.
- Automated tests failed.
- Integration results.
- Physical-device tests.
- Regressions discovered and resolved.
- Tests not performed.

Never claim a test was performed if it was not.

## 13.10 Final status

Use one of:

- `FULLY_DONE`
- `PARTIALLY_DONE`
- `BLOCKED`

`FULLY_DONE` is permitted only when all required acceptance criteria are satisfied and physically verified where physical verification is required.

If something is blocked, explain the exact blocker, evidence, and next action.

## 13.11 Rollback

Include exact commands or procedures to restore the last known-good userspace state.

---

# 14. Definition of done

## A. Doom

- [ ] Doom launches from Nuxel.
- [ ] Correct game data is detected.
- [ ] Sound is enabled by default.
- [ ] Music is enabled by default where supported.
- [ ] Effects are enabled by default.
- [ ] Audio uses a working Nuxel route.
- [ ] Physical speaker output verified.
- [ ] Controls work.
- [ ] Exit cleans up audio and surfaces.
- [ ] Relaunch works without manual configuration.

## B. Top bar

- [ ] Incorrect fullscreen top bar removed from active implementation.
- [ ] Desktop top bar is the one authoritative implementation.
- [ ] Fullscreen apps reveal the standard Nuxel bar.
- [ ] First downward swipe opens standard bar.
- [ ] Second opens expanded Quick Settings.
- [ ] Third opens extended Quick Settings.
- [ ] One upward swipe closes everything.
- [ ] No partial collapse.
- [ ] Landscape top swipe area improved.
- [ ] Landscape bottom navigation area improved.
- [ ] No duplicate gesture listeners.
- [ ] No hidden input-blocking surface.
- [ ] Fullscreen app remains correctly displayed.

## C. Startup performance

- [ ] Native launch path measured.
- [ ] Flatpak launch path measured.
- [ ] Cold and warm startup measured.
- [ ] Bottlenecks identified from evidence.
- [ ] Safe improvements implemented.
- [ ] Launcher remains responsive.
- [ ] Flatpak sandboxing preserved.
- [ ] Before/after metrics included.

## D. Dark theme

- [ ] GTK 3 default verified.
- [ ] GTK 4 default verified.
- [ ] libadwaita behavior verified.
- [ ] Portal color-scheme preference verified.
- [ ] Flatpak propagation verified.
- [ ] System Monitor checked.
- [ ] Representative apps checked.
- [ ] Reboot persistence verified.
- [ ] No unnecessary per-app configuration required for supported apps.

## E. Back lifecycle

- [ ] Single Back works.
- [ ] App internal Back still works.
- [ ] Modal Back still works.
- [ ] App-root Back returns to Home.
- [ ] Invisible surface issue fixed.
- [ ] Stale input region removed.
- [ ] Focus restored.
- [ ] Home immediately interactive.
- [ ] Long-Back behavior preserved.
- [ ] Repeated physical tests completed.

## F. Desktop geometry

- [ ] Desktop vertical position restored.
- [ ] Top bar visible and correctly positioned.
- [ ] Four docked icons correctly positioned.
- [ ] No unexplained blank gap.
- [ ] Bottom triple-button navigation aligned.
- [ ] No stale transforms.
- [ ] No duplicate inset calculations.
- [ ] Portrait verified.
- [ ] Landscape verified.
- [ ] Fullscreen application exit verified.
- [ ] Repeated app transitions verified.

## G. System stability

- [ ] Existing Home behavior preserved.
- [ ] Existing Back behavior preserved.
- [ ] Existing Tabs behavior preserved.
- [ ] App drawer works.
- [ ] Existing audio remains functional.
- [ ] Quick Settings controls remain functional.
- [ ] No second framebuffer writer.
- [ ] No forced software rendering.
- [ ] No weakened Flatpak sandbox.
- [ ] No boot-critical partition modifications.
- [ ] Rollback documented.
- [ ] Final report created.

---

# 15. Final instruction

Do not deliver a superficial patch.

Do not stop after analyzing the code.

Do not merely write recommendations.

Do not hide incorrect UI with CSS.

Do not replace lifecycle correctness with long-Back termination.

Do not fix desktop displacement by changing the global resolution.

Do not claim every GTK application is dark without testing the actual installed applications.

Do not claim Doom sound works until actual audio output has been verified.

**Investigate the real Nuxel implementation, identify the root causes, implement all six workstreams, run the complete test suite, deploy safely to the verified S10+, physically test the required behavior, and produce `REPORT-PWNAGE-94000.md`.**

The result must feel like a properly integrated mobile Linux operating system, not a desktop environment held together by workarounds.

**PWNAGE-94000 — EXECUTE THE COMPLETE SPECIFICATION.**
