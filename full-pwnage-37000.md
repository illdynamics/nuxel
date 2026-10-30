# PWNAGE-37000 — NUXEL BUTTERSCOTCH PERFORMANCE ENGINEERING
## FBDEV-FRIENDLY • PIXEL-ART ARCADE UI • MINIMAL COMPOSITING • MAXIMUM RESPONSIVENESS

## 0. Mission

You are working on Nuxel, a custom Fedora-based ARM64 Linux phone OS. The current test target is the Samsung Galaxy S10+ SM-G975F (`beyond2lte`), historically running a Fedora 43-based userspace and Linux 4.14.253 kernel. Inspect the current device and repository rather than assuming these details have not changed.

The goal is a substantial improvement in real-world responsiveness, frame pacing, input latency, memory efficiency, and overall usability.

Nuxel has its own identity: an 8-bit arcade-inspired Linux phone with pixel penguins, playful animations, bold colors, custom icons, and a distinct visual style.

**Keep the personality. Remove the waste.**

Do not turn Nuxel into a generic grey interface. Do not remove all motion or color. Instead, replace expensive effects with crisp, inexpensive visual design and optimize the underlying software so the device feels immediate.

This is an implementation mission. Inspect, measure, diagnose, modify, test, deploy safely, and document. Do not stop after producing a proposal.

## 1. Non-negotiable constraints

- Preserve Nuxel's recognizable 8-bit arcade style.
- Prefer lightweight, framebuffer-friendly rendering where compatible with the existing graphics stack.
- Determine the actual rendering backend before choosing backend-specific optimizations.
- Do not assume fbdev is the active backend merely because it is desirable.
- Do not replace the kernel, flash firmware, modify partitions, or change the bootloader.
- Do not introduce a heavyweight desktop environment, renderer, graphics library, or dependency solely for visual polish.
- Do not remove essential functionality or hide broken features.
- Do not fake responsiveness with premature success indicators.
- Preserve application state, navigation semantics, keyboard behavior, touch usability, and console recovery.
- Preserve the existing safe deployment and rollback workflow.
- Do not overwrite unrelated user changes.
- Back up configuration files before changing them.
- Do not use arbitrary sleeps as synchronization or infinite loops as animation mechanisms.
- Do not sacrifice stability or security for benchmark results.
- Test on the actual device whenever hardware behavior or rendering performance depends on it.
- If physical-device testing is unavailable, clearly label the result as unverified.

Create or update `docs/pwnage-37000.md`. Store genuine benchmark results and test logs in the project's established evidence directory, preferably `docs/beta-finalization/live/evidence/pwnage-37000/` if that layout remains in use.

---

# PHASE 1 — RECONNAISSANCE AND PERFORMANCE BASELINE

## 1.1 Inspect the complete rendering path

Identify:

- The UI framework and application architecture.
- The actual renderer used by the deployed build.
- Whether the current path uses fbdev, DRM/KMS, EGL/OpenGL, software rendering, a framebuffer-backed toolkit, WebKit/WebView, HTML/CSS, or another mechanism.
- Whether rendering is performed by one process or several.
- How touch and button events reach the UI.
- How screen updates are scheduled.
- How the top bar, dock, desktop, app view, keyboard, overlays, and navigation bar are composed.
- How pixel-art assets are loaded, decoded, cached, scaled, and displayed.
- Whether the system uses a compositor and whether transparency creates additional rendering or memory overhead.
- Which animations remain active while the interface is idle.
- Whether the UI runs on the main thread or an event-driven loop.
- Whether system calls, filesystem operations, subprocesses, or network operations can block rendering.

Inspect existing documentation, recent changes, tests, launch scripts, service definitions, and performance-related settings before implementing anything.

Do not assume that a technique which works in a browser-based UI will also help a native framebuffer renderer.

## 1.2 Establish reproducible baseline measurements

Record what the current build actually does.

Measure, where supported:

- Touch-to-visible-response latency.
- Button-to-visible-response latency.
- Frame duration distribution and frame-time spikes.
- Scrolling smoothness and input responsiveness.
- Time to open and minimize applications.
- Back/Home/Tabs response time.
- Keyboard opening, typing, and dismissal.
- Quick-settings interaction latency.
- CPU use during idle, animation, scrolling, and app switching.
- Resident memory and memory growth over repeated interactions.
- Asset loading and image decoding time.
- Startup time until the interface is interactive.
- Rendering behavior under concurrent background activity.

Use existing tools or add lightweight instrumentation. Do not leave expensive debug instrumentation enabled in the production path.

Record the methodology, build version, test scenario, and measurement units.

If the hardware does not expose reliable frame timing, use the most defensible available measurements and document the limitation. Do not invent frames-per-second results or claim that a visual impression is a benchmark.

## 1.3 Build a bottleneck map

Identify the most expensive paths and rank them by user impact.

For each candidate bottleneck, document:

- What the user experiences.
- Which code or process is responsible.
- The evidence.
- The proposed change.
- The expected trade-off.
- How the fix will be tested.

Prioritize repeated, user-visible costs rather than isolated micro-optimizations that make no perceptible difference.

---

# PHASE 2 — CREATE A LIGHTWEIGHT ARCADE VISUAL PROFILE

## 2.1 Introduce a coherent rendering policy

Create or refine a centralized visual-performance configuration if the existing architecture supports it.

The configuration should express the visual principles consistently across the desktop, app views, navigation, menus, quick settings, and lockscreen.

Prefer existing theme/configuration mechanisms. Do not introduce multiple competing theme systems.

The lightweight profile should be the default on the target device unless an existing user preference or platform requirement says otherwise.

Where practical, make expensive optional effects individually configurable so they can be disabled without breaking the interface.

## 2.2 Reduce expensive effects

Inspect the actual code and minimize unnecessary use of:

- Large blurred backgrounds.
- Backdrop filters.
- Heavy drop shadows.
- Multi-layer glow effects.
- Repeated alpha blending over large regions.
- Large transparent overlays.
- Complex gradient stacks.
- Animated background noise.
- Excessive box-shadow or text-shadow layers.
- Expensive masks and clipping.
- Full-screen scaling and filtering.
- Continuous opacity or transform animations.
- Repeated CSS filters or image-processing operations.
- Re-rendering the entire UI when one status icon changes.

Remove or simplify effects that consume meaningful resources without providing essential usability.

Do not blindly remove every alpha channel from images. Transparent PNG sprites may be integral to the design and inexpensive to render when used appropriately. Optimize the actual drawing path and asset size.

## 2.3 Replace glow with pixel-art character

Preserve visual identity through cheaper techniques:

- Crisp sprite silhouettes.
- Strong foreground/background contrast.
- Flat color panels.
- Carefully chosen accent colors.
- Pixel borders and small highlights.
- Limited-frame sprite animations.
- Small, static decorative elements.
- Discrete visual states rather than continuously animated effects.
- Lightweight state changes such as icon swaps or simple position transitions.
- Short transitions that do not block interaction.

Use visual hierarchy and good spacing instead of blur and transparency.

Keep the penguin characters recognizable. Preserve their colors, expressions, and established visual language.

Where a glowing element is important to the aesthetic, first try a static bright accent, pixel outline, or small sprite highlight instead of a large animated blur.

Do not regenerate, replace, or redesign existing assets unless a measured asset problem justifies the change.

## 2.4 Animation policy

Keep the interface lively without allowing animation to dominate the rendering budget.

For every animation:

1. Identify its user-facing purpose.
2. Determine whether it must run continuously.
3. Bound its duration and frequency.
4. Avoid expensive effects on every frame.
5. Avoid animation work when the element is hidden.
6. Avoid updating static elements unnecessarily.
7. Ensure input remains available throughout the animation.
8. Stop or pause work when the owning UI is no longer visible, where appropriate.

Use short, lightweight transitions for app opening, minimizing, and menu presentation. Avoid long animations that make actions feel slow.

Prefer a few intentional animation frames over high-frequency decorative motion when the latter offers no real UX benefit.

Do not introduce animation delays before an action takes effect. The action should happen immediately; the animation should communicate the transition.

---

# PHASE 3 — FBDEV-FRIENDLY AND SOFTWARE-RENDERING OPTIMIZATION

## 3.1 Optimize the existing backend

The requirement is framebuffer-friendly behavior, not blindly forcing a specific graphics API.

First determine whether the current deployment uses fbdev, DRM/KMS, EGL/OpenGL, a toolkit abstraction, a browser engine, or a different path.

Then apply the optimizations that match that backend.

If Nuxel already uses a framebuffer-backed renderer, optimize that path directly.

If Nuxel currently uses DRM/KMS or another established renderer, retain it unless measurements prove a safe, substantial benefit from a change. Do not migrate the entire graphics stack as part of this mission.

## 3.2 Framebuffer-oriented principles

Where the actual backend supports them:

- Avoid unnecessary full-screen framebuffer writes.
- Track damaged regions and update only changed areas.
- Avoid repeated conversion between image formats.
- Reuse compatible pixel buffers.
- Minimize allocations in the render loop.
- Avoid repeatedly scaling the same sprites.
- Cache static background and panel content when safe.
- Use efficient blitting or the renderer's equivalent optimized image-copy operations.
- Avoid copying large buffers when an in-place or region-based update is supported.
- Keep pixel formats and row strides correct.
- Respect framebuffer dimensions, stride, and supported pixel formats.
- Avoid expensive per-pixel operations in interpreted code.
- Avoid excessive synchronization between rendering and input.
- Do not redraw static UI elements simply because a timer fired.

Use the fastest appropriate path already supported by the device and software stack.

## 3.3 Do not introduce framebuffer hazards

- Do not write directly to a framebuffer behind the active compositor or renderer.
- Do not bypass the toolkit's rendering ownership without understanding the consequences.
- Do not assume a fixed screen resolution or pixel format.
- Do not hard-code framebuffer device paths without inspecting the deployed configuration.
- Do not break rotation, display initialization, touch mapping, or suspend/resume.
- Do not introduce tearing or stale display regions in pursuit of fewer draw calls.
- Do not assume direct framebuffer access is available or appropriate on the current device.

If the backend does not support a proposed optimization, choose the correct equivalent or document why it is not applicable.

---

# PHASE 4 — OPTIMIZE THE UI EVENT LOOP AND INPUT LATENCY

## 4.1 Keep the main interaction path nonblocking

Trace touch input from the initial event through the state update and visible result.

Find and eliminate unnecessary synchronous work from the interaction path, including:

- Subprocess startup and waiting.
- Synchronous filesystem operations.
- Network calls.
- Expensive asset decoding.
- App discovery and metadata scanning.
- Repeated state reconstruction.
- Large serialization/deserialization tasks.
- Unnecessary IPC.
- Excessive logging.
- Long-running callbacks.
- Synchronous service-status polling.

Move suitable operations to background workers or asynchronous APIs while preserving clear ownership of UI state.

Do not move every task to a worker indiscriminately. Use appropriate scheduling and avoid creating so many workers that they compete with the renderer.

## 4.2 Fast feedback, honest results

When a user taps a control, acknowledge the input promptly.

For a slow operation:

- Provide immediate visual acknowledgment.
- Keep the UI responsive.
- Show a truthful pending or progress state.
- Update the interface from the authoritative result.
- Recover gracefully from failure.

Do not claim that a Wi-Fi toggle, reboot, file operation, or application transition succeeded before the underlying operation has been accepted or completed as appropriate.

Do not use arbitrary timers to fake responsiveness.

## 4.3 Remove redundant work

Inspect for:

- Duplicate event listeners.
- Repeated subscriptions.
- Unbounded timers.
- Polling where event-driven updates are available.
- Repeatedly calculated layout values.
- Repeatedly decoded sprites.
- Unnecessary component or view reconstruction.
- Excessive DOM updates, if a web-based UI is in use.
- Excessive signal/slot churn, if a native toolkit is in use.
- Repeated process launches.
- Background work that continues after the corresponding UI has been dismissed.

Clean up subscriptions and timers when components or views are destroyed or no longer need updates.

Ensure that repeatedly opening and closing panels does not accumulate handlers, processes, or memory.

---

# PHASE 5 — ASSET, IMAGE, AND FONT EFFICIENCY

## 5.1 Audit the assets

Inventory the assets actually used by the deployed UI.

Look for:

- Oversized images displayed at small sizes.
- Multiple duplicate copies of the same asset.
- Unnecessarily large sprite sheets.
- Repeated decoding of the same images.
- Assets loaded synchronously during navigation.
- Incorrect image scaling.
- Excessive runtime filters.
- Assets loaded even when their views are not used.
- Repeated font loading or expensive text measurement.

Optimize only where there is a demonstrated benefit.

## 5.2 Preserve the Nuxel look

Maintain the current design language and reuse existing assets where possible, including the established penguin, lockscreen, boot, dock, status-indicator, and navigation artwork.

Do not substitute generic icons for custom Nuxel artwork just to reduce a negligible amount of memory.

Keep text legible at the device's actual resolution. Avoid unnecessary font effects, but do not sacrifice readability.

## 5.3 Cache intelligently

Cache decoded assets, static backgrounds, or precomputed layouts where it helps.

Requirements:

- Bound memory use.
- Invalidate caches when the underlying asset or relevant theme changes.
- Avoid duplicating large image buffers.
- Avoid retaining entire screens indefinitely.
- Release resources when appropriate.
- Measure whether caching improves the actual target device.

A cache that makes the phone run out of memory is not an optimization.

---

# PHASE 6 — APP SWITCHING, NAVIGATION, AND LAYERING

Performance optimization must not regress core navigation.

Inspect the interaction between:

- Foreground app.
- Background or minimized apps.
- Desktop.
- Dock.
- Top status bar.
- Bottom Back/Home/Tabs navigation.
- Quick-settings overlay.
- Keyboard.
- Lock screen.
- Modal dialogs.

Ensure these layers have clear ownership and deterministic visibility.

Back, Home, and Tabs must remain correct after the optimization pass. Do not accidentally restore previous behavior where the four bottom desktop apps move over the foreground app instead of minimizing it properly.

Optimize app transitions without reconstructing the whole desktop unnecessarily.

Preserve application state when intended. Avoid restarting an application simply because it was minimized.

Ensure app switching does not leak memory or leave hidden animation loops running.

The dock must remain in its intended layer and must not obscure app content or the bottom navigation controls.

---

# PHASE 7 — QUICK SETTINGS AND SYSTEM INTEGRATION

Inspect the status bar and quick-settings update path.

Avoid refreshing the entire interface when only battery percentage, Wi-Fi state, charging state, or another small indicator changes.

Use authoritative state events where possible and keep updates lightweight.

Avoid high-frequency polling for battery, Wi-Fi, connectivity, and service status unless the platform genuinely requires it.

Do not make the UI wait for hardware initialization before becoming interactive.

A slow underlying operation must not freeze unrelated controls.

Preserve the accuracy of status indicators. Do not show a connected state until the connection exists.

If a system operation is slow because of a genuine driver or service limitation, optimize the UI path without concealing the underlying failure.

---

# PHASE 8 — MEMORY, CPU, AND BACKGROUND ACTIVITY

Measure idle and active resource use.

Inspect for:

- Leaking views or application instances.
- Retained image buffers.
- Excessive timer activity.
- Unbounded log growth.
- Excessive background polling.
- Repeatedly spawned processes.
- Memory fragmentation or allocation churn.
- CPU-heavy idle animations.
- Duplicate system services.
- Background work that never terminates.
- Unnecessary network checks.
- Excessive UI refresh frequency.

Keep the phone usable under memory pressure and after repeated app switching.

Avoid adding a watchdog that continuously restarts healthy processes or a performance daemon that burns more CPU than the work it monitors.

Do not globally lower system security or disable essential services to reduce resource use.

If a process consumes significant resources, establish why before killing, disabling, or replacing it.

---

# PHASE 9 — STARTUP AND RESPONSIVENESS UNDER LOAD

Determine whether boot-time work competes with user interaction.

Prioritize essential readiness:

1. Display and input are usable.
2. The lockscreen or expected entry UI becomes available.
3. Essential navigation remains responsive.
4. Noncritical background services initialize without blocking interaction.
5. Secondary UI content and optional status updates settle in as available.

Respect the existing startup design, including PWNAGE-31000's preloading animation if already implemented.

Do not let the preloading video delay essential initialization, and do not delay the lockscreen merely to complete optional cosmetic work.

Do not use arbitrary sleeps to coordinate services.

Measure actual time to interaction rather than only the time a splash screen appears.

---

# PHASE 10 — AUTOMATED TESTS AND REGRESSION COVERAGE

Create or extend tests for the actual rendering and interaction architecture.

At minimum, cover:

### Rendering
- Static screen does not continuously trigger unnecessary redraws.
- Small status changes do not force a complete redraw when avoidable.
- Asset caching does not grow without bounds.
- Animations stop when their elements are hidden.
- Layout remains correct at the actual device resolution.
- Pixel-art assets remain crisp and correctly scaled.

### Input
- Touch events remain responsive during background work.
- Repeated taps do not create duplicate operations.
- Animations do not block Back/Home/Tabs.
- Keyboard opening and dismissal remain responsive.

### Navigation
- Back, Home, and Tabs retain correct semantics.
- Minimized applications are not displayed over the desktop.
- App switching does not create duplicate instances unexpectedly.
- Dock, app content, and navigation controls remain in the correct layers.

### Resource usage
- Repeated app opening and closing does not cause unbounded memory growth.
- Hidden panels do not continue unnecessary polling.
- Idle CPU usage remains low.
- Background operations do not freeze the UI.

### System integration
- Quick settings remain interactive during initialization.
- Status indicators reflect real state.
- Startup remains functional when optional assets are missing.
- Errors do not leave the interface permanently unresponsive.

Use automated tests wherever practical, but do not mistake a successful unit test for proof of smooth rendering on physical hardware.

---

# PHASE 11 — PHYSICAL-DEVICE VALIDATION

Test the deployed build on the S10+ whenever possible.

Run a consistent set of scenarios before and after the changes:

1. Cold boot to usable lockscreen.
2. Unlock and navigate to the desktop.
3. Open and minimize several applications repeatedly.
4. Rapidly switch between apps using Tabs.
5. Scroll through content.
6. Open and dismiss the keyboard repeatedly.
7. Type rapidly.
8. Open and use quick settings.
9. Use the phone while background services initialize.
10. Leave the phone idle and observe resource usage.
11. Repeat the workload to check for performance degradation.

Check for:

- Visible frame drops.
- Delayed input.
- Stuck animations.
- Flickering or tearing.
- Stale display regions.
- Incorrect pixel scaling.
- Navigation regressions.
- Memory growth.
- Excessive CPU usage.
- Crashes or process restarts.

Record the exact build and test conditions.

Use comparable conditions for before/after tests. Avoid claiming improvement from runs with substantially different workloads or background activity.

---

# PHASE 12 — SAFE DEPLOYMENT

Inspect the project's current build and deployment procedure.

- Preserve existing uncommitted work.
- Run the appropriate test suite before deployment.
- Back up any changed configuration.
- Deploy through the established safe workflow.
- Preserve USB, serial, and WLAN recovery paths.
- Do not flash the kernel or firmware.
- Do not repartition or reset the device.
- Verify the running build after deployment.
- Keep a clear rollback path.

If a change requires a graphics-stack replacement or another risky system modification, do not perform it automatically. Demonstrate why it is necessary and complete safe, compatible optimizations first.

---

# PHASE 13 — REQUIRED REPORT

Create or update `docs/pwnage-37000.md`.

Include:

## 13.1 Architecture findings
- Actual UI framework.
- Actual rendering backend.
- Whether fbdev is in use or merely a compatibility target.
- Main performance bottlenecks discovered.
- Relevant hardware or backend limitations.

## 13.2 Visual optimization
- Expensive effects removed or simplified.
- Arcade identity and animations preserved.
- Asset and rendering optimizations.
- Any configurable performance profile added.

## 13.3 Code changes
- Every modified file.
- The reason for each change.
- Architectural decisions and trade-offs.

## 13.4 Before-and-after results
Include actual measurements where available:

- Input latency.
- Frame timing.
- App switching.
- Scrolling.
- Keyboard responsiveness.
- CPU usage.
- Memory usage.
- Startup to interactive UI.
- Idle behavior.

Clearly label unavailable measurements. Do not invent values.

## 13.5 Testing
- Automated tests and results.
- Physical-device tests and results.
- Regression tests.
- Any remaining visual or functional issues.

## 13.6 Deployment and rollback
- Whether the build was deployed.
- The tested commit or build identifier.
- How to roll back.
- Any remaining manual steps.

## 13.7 Remaining blockers
For every unresolved bottleneck, identify the actual limiting layer where possible: application code, toolkit, renderer, userspace, driver, kernel, or hardware.

Explain the next safe step without silently expanding the scope.

---

# DEFINITION OF DONE

- [ ] The current renderer has been identified and optimized appropriately.
- [ ] Nuxel retains its 8-bit arcade identity and recognizable penguin personality.
- [ ] Resource-heavy glow, blur, transparency, and compositing have been reduced where measurements justify it.
- [ ] Pixel-art rendering remains crisp and correctly scaled.
- [ ] Input handling and visible UI updates are measurably more responsive.
- [ ] Animations remain lightweight and never block interaction.
- [ ] App switching and navigation remain correct.
- [ ] Quick settings and status indicators remain responsive and accurate.
- [ ] Idle resource use is controlled.
- [ ] Repeated use does not reveal obvious memory leaks or accumulating background work.
- [ ] Startup and the preloading/lockscreen sequence remain correct.
- [ ] Automated tests pass.
- [ ] Physical-device results are documented honestly.
- [ ] Deployment and rollback are documented.
- [ ] No unsafe kernel, firmware, bootloader, or partition modifications were performed.

## FINAL DIRECTIVE

Do not optimize for screenshots. Optimize for the person holding the phone.

Every tap should feel immediate. Every transition should feel intentional. Scrolling should feel light. The keyboard should appear without a noticeable fight. Applications should switch cleanly. The desktop should stay stable. The penguin can dance, but it should not melt the CPU doing it.

Keep the style. Lose the bloat. Measure the results. Make Nuxel BUTTERSCOTCH BUTTERSMOOTH.

PENGUIN GO BRRR. 🐧⚡
