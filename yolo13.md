# NUXEL — GALAXY S10+ BETA FINALIZER
## DeepSeek V4 Flash Thinking HIGH · CodeSeeQ · A30 → BETA 0.1
### EXISTING UTM LAUNCHER · STATIC WALLPAPER · PHYSICAL TOUCH · FLICKER-FREE DISPLAY · WORKING APPLICATIONS

# 1. YOUR MISSION

You are the autonomous lead engineer responsible for completing the first genuinely usable beta of Nuxel, our Fedora-based Linux PHONE operating system, on the Samsung Galaxy S10+.

This mission continues directly from engineering cycles A27, A28, A29 and A30.

**DO NOT START NUXEL OVER.**

**DO NOT BUILD ANOTHER LAUNCHER.**

**DO NOT REPLACE OUR EXISTING UTM GUI WITH A RECREATION.**

**DO NOT USE IMAGE-ANALYSIS OR SCREENSHOT-INTERPRETATION TOOLS.**

The user already has the CORRECT Nuxel launcher running inside the UTM virtual machine RIGHT NOW.

Your job is to inspect that running VM through its terminal, processes, services and application code, and get the exact same launcher implementation operating correctly on the physical Samsung.

The real phone already has:

- Working ARM64 kernel.
- Fedora 43 rootfs.
- Functional systemd startup.
- Working AMOLED framebuffer.
- Original Nuxel boot animation.
- USB CDC-ACM live console.
- Live software deployment.
- Phoc headless Wayland compositor.
- WebKitGTK installed.
- A29 Wayland-to-framebuffer graphics bridge.
- Physical touchscreen IRQ and evdev evidence.

But it still has serious beta blockers:

1. The expected full Nuxel launcher isn't reliably appearing.
2. The wallpaper is missing or incorrect.
3. Touch input is not controlling the launcher.
4. The boot animation flickers.
5. Animation frames appear through or over the launcher.
6. Launcher applications are not all activating correctly.
7. Some startup and graphics ownership fixes remain provisional.
8. Release validation is incomplete.

Your objective is to FIX THESE, not produce another architectural assessment.

---

# 2. MANDATORY PRIORITIES

Follow the user's priority order.

## P1 — CORRECT ORIGINAL UTM LAUNCHER

Get the exact existing Nuxel Home PWA running and displayed correctly on the S10+.

No substitute launcher.

No fake app registry.

No alternative layout.

No placeholder dashboard.

## P2 — ORIGINAL STATIC NUXEL WALLPAPER

Set:

`./assets/nuxel-background.png`

as the actual home-screen wallpaper.

Preserve the VM's existing launcher styling and application presentation.

## P3 — WORKING PHYSICAL TOUCHSCREEN

The user must be able to control the launcher with actual finger taps and swipes.

Not simulated taps.

Not USB console commands.

Not merely a registered input device.

## P4 — CLEAN ANIMATION AND DISPLAY OWNERSHIP

Eliminate:

- Second-stage boot-animation flickering.
- Animation frames appearing through the launcher.
- Duplicate framebuffer writers.
- Unnecessary framebuffer reinitialization.
- Redundant PWA boot-animation overlays.
- Black flashes during animation-to-launcher handoff.

## P5 — BETA READINESS

Finish application launching, runtime stability, recovery, performance, reproducibility and acceptance testing.

Do not claim beta readiness until the mandatory physical tests pass.

---

# 3. WORK LIVE — NO PLANNED TWRP

**THE SAMSUNG IS CURRENTLY BOOTED INTO NUXEL.**

All ordinary work must happen through the working live USB console.

Project root:

`~/x/nuxel`

Live tooling:

`scripts/s10plus-debug-pack/nuxel-live.sh`

`scripts/s10plus-debug-pack/nuxel-live-deploy.sh`

Existing A29 transport utility:

`tools/s10plus/a29/push-file.sh`

Do not reboot to TWRP for:

- Launcher files.
- CSS.
- JavaScript.
- Icons.
- Wallpaper.
- WebKit host changes.
- Touchscreen userspace.
- Phoc configuration.
- Graphics bridge userspace.
- Systemd services.
- Application assets.
- Local bridge APIs.

Use:

`INSPECT → PATCH → BUILD → VERIFY → DEPLOY LIVE → RESTART AFFECTED SERVICE → TEST → ROLLBACK IF NECESSARY`

Do not flash BOOT from the running system.

If a kernel or embedded-initramfs fix is eventually unavoidable, build and validate it separately, but do not interrupt this mission with speculative flashing.

TWRP remains an emergency recovery tool.

There is no automatic TWRP-return agreement in this mission.

---

# 4. EXACT REPOSITORY AREAS

Authoritative launcher:

`pwa/nuxel-home/`

Launcher files:

`pwa/nuxel-home/index.html`

`pwa/nuxel-home/js/apps.js`

`pwa/nuxel-home/js/app.js`

`pwa/nuxel-home/js/launcher.js`

`pwa/nuxel-home/css/style.css`

`pwa/nuxel-home/css/launcher.css`

`pwa/nuxel-home/css/search.css`

`pwa/nuxel-home/css/status-bar.css`

Shared web functionality:

`pwa/nuxel-common/`

Application sources:

`pwa/nuxel-apps/`

Native applications:

`shell/`

Runtime services:

`services/`

UTM infrastructure:

`vm/`

Wallpaper:

`assets/nuxel-background.png`

Animation:

`assets/nuxel-boot-animation.mp4`

S10+ engineering:

`tools/s10plus/a27/`

`tools/s10plus/a28/`

`tools/s10plus/a29/`

`tools/s10plus/a30/`

Relevant source:

`tools/s10plus/a29/nuxel-wl-fb.c`

`tools/s10plus/a29/nuxel-pwa-host.c`

`tools/s10plus/a29/nuxel-touch-arm.c`

`tools/s10plus/a29/nuxel-session.sh`

Current Fedora image builder:

`images/s10plus/build-phone-rootfs-inside-fedora.sh`

Documentation:

`docs/s10plus-autonomous-boot-repair/UTM-LAUNCHER-PORT/`

Inspect the actual repository state before executing.

Prior modifications may have changed since these snapshots.

---

# 5. FIRST ACTION — INSPECT BOTH RUNNING SYSTEMS

You have TWO live development targets.

## Target A — The working UTM VM

The user has already started the VM and it is displaying the correct launcher.

Use the MacBook's UTM/terminal tooling to inspect its runtime.

Potential commands include:

`utmctl list`

`utmctl status`

`ssh`

`systemctl`

`ps`

`ss`

`curl`

`rpm`

Do not assume the guest address is permanent.

Earlier records used:

`nuxel@192.168.64.3`

Discover and verify the actual VM address or access method.

Inside the VM, determine:

- Exact launcher executable.
- Exact running WebKitGTK process.
- Actual launcher URL.
- Application session.
- Phoc configuration.
- Web server configuration.
- Browser process arguments.
- Loaded CSS/JS paths.
- Application registry.
- App activation mechanism.
- Native bridge/API services.
- Actual runtime dependencies.
- App asset paths.

## Target B — Physical Samsung S10+

Connect through the existing Nuxel live console.

Verify:

`uname -a`

`cat /etc/os-release`

`systemctl is-system-running`

`systemctl --failed`

`systemctl status nuxel-wayland`

`systemctl status nuxel-wl-fb`

`systemctl status nuxel-touch-arm`

`systemctl status nuxel-ui`

Check:

`/run/nuxel-home.state`

`/run/nuxel-wl-fb.state`

`/run/nuxel-touch-arm.state`

`/run/nuxel-session.log`

`/var/lib/nuxel/animation`

`/var/lib/nuxel/anim-stop`

`/run/nuxel-launcher-ready`

The exact files may have changed; inspect the current source.

Compare the running UTM processes against the running S10+ processes.

**DO NOT USE SCREENSHOTS FOR THIS COMPARISON.**

Use executable identity, process arguments, loaded assets, URLs, DOM/source definitions, service state and file hashes.

Produce a concise, evidence-backed runtime-difference report.

---

# 6. CONFIRMED FACT — THE UTM LAUNCHER IS THE PWA

Previous A28/A29 analysis established that the VM's actual launcher is:

**Nuxel Home PWA — `pwa/nuxel-home/`**

It runs using WebKitGTK.

It is served on:

`127.0.0.1:8000`

The actual application registry is:

`pwa/nuxel-home/js/apps.js`

The A28 record identified nine applications, with three docked.

The VM uses:

- Fedora 43.
- Phoc.
- Wayland.
- WebKitGTK.
- The existing Nuxel Home PWA.

The Samsung's current kernel lacks DRM/KMS, but A29 implemented a compatible route:

`Phoc headless + Pixman`

→ `WebKitGTK Nuxel Home PWA`

→ `Wayland screencopy`

→ `nuxel-wl-fb`

→ `Samsung DECON framebuffer`

This is already the correct architectural direction.

**DO NOT GO BACK TO THE A27/A28 REIMPLEMENTED LAUNCHER.**

Instead, fix and finish this A29/A30 implementation.

Check that the current S10+ isn't silently falling back to the A27 UI.

Prove:

- The WebKitGTK PWA host is alive.
- The correct URL is loaded.
- The complete page loads successfully.
- CSS loads.
- JS modules load.
- App registry initializes.
- Application icons resolve.
- The intended WebKit window receives input.
- Phoc produces frames.
- The bridge commits frames.
- No other launcher owns the framebuffer.

If any step fails, fix that step.

---

# 7. CRITICAL ISSUE — PREVIOUS A29 SESSION HAD MISSING PWA ASSETS

The A29b record identified a source-level problem:

The launcher imports:

`../nuxel-common/bridge.js`

But the original S10+ rootfs staged only:

`pwa/nuxel-home`

rather than the complete required PWA tree.

That caused HTTP 404 responses.

A29b claims to have corrected the docroot and staged:

`/usr/share/nuxel/pwa/`

Verify that this fix is still active in the current runtime.

Require HTTP 200 and correct content for:

- `/pwa/nuxel-home/index.html`
- Launcher CSS.
- Launcher JavaScript.
- `/pwa/nuxel-common/bridge.js`
- Application manifests.
- Application icons.
- PWA application pages.
- Shared assets.

Check actual Content-Type responses.

Do not count a successful HTML request as a complete application load.

Audit browser console errors and WebKit load failures using logs and programmatic instrumentation, NOT screenshots.

If the PWA is loading stale files due to service-worker caching, implement a controlled cache/version migration rather than repeatedly deleting browser state at random.

The physical system must serve the same authoritative launcher source as the UTM VM.

---

# 8. CRITICAL ISSUE — THE REAL STATIC WALLPAPER IS MISSING

The current repository contains:

`assets/nuxel-background.png`

But the PWA's stylesheet references:

`../assets/nuxel-background.png`

relative to:

`pwa/nuxel-home/css/style.css`

That resolves to:

`pwa/nuxel-home/assets/nuxel-background.png`

The source archive does not contain that wallpaper at this expected PWA path.

**THIS IS A CONCRETE ASSET-PATH BUG.**

Fix it properly.

Options:

- Stage the authoritative asset at the expected PWA path.
- Or update the stylesheet to reference a stable absolute, correctly served asset URL.
- Or use the existing deployment asset mechanism if it already defines the correct path.

Choose the most maintainable solution.

Do not create another background image.

Do not alter the supplied artwork.

Verify:

1. Source asset hash.
2. Deployed asset hash.
3. HTTP 200.
4. Correct image MIME type.
5. Correct dimensions.
6. Successful decoding by the browser.
7. Computed CSS background-image references the intended URL.
8. The wallpaper is present beneath the launcher UI.
9. It remains static during normal home-screen operation.

Preserve the original CSS design and intended layout.

Do not replace the launcher with a custom bitmap rendering just to display the wallpaper.

**P2 ACCEPTANCE: THE ORIGINAL NUXEL WALLPAPER IS SERVED AND USED BY THE REAL PWA.**

---

# 9. CRITICAL ISSUE — MULTIPLE BOOT ANIMATIONS

We have at least two independent boot-animation mechanisms.

## Animation A — OS/initramfs animation

Nuxel already displays its original MP4-derived boot animation before the graphical launcher is available.

This is the system boot animation.

It is controlled through the initramfs animation process and Nuxel animation-state files.

## Animation B — PWA fullscreen video overlay

The actual Nuxel Home PWA includes:

`<div id="boot-splash">`

and:

`<video id="boot-splash-video">`

in:

`pwa/nuxel-home/index.html`

Its CSS gives the overlay an extremely high z-index.

Its JavaScript in:

`pwa/nuxel-home/js/app.js`

tries to preserve the splash for a minimum playback period, and has a 12-second timeout.

**ON THE PHYSICAL S10+, THIS IS A REDUNDANT SECOND BOOT ANIMATION.**

The OS has already displayed the animation before the PWA starts.

The user reports animation content flashing through the launcher.

## Required fix

Implement a phone-runtime boot-animation ownership policy.

For the S10+ native boot path:

- The OS animation is authoritative.
- The launcher must not start a second fullscreen animation.
- The PWA must become visually ready without requiring another MP4 playback.
- No fullscreen video overlay may cover the launcher after the graphical handoff.
- The PWA must not spend 3–12 seconds waiting for a redundant splash.

Prefer a well-defined launch-mode signal, such as a startup configuration or query parameter indicating that the OS has already played the animation.

Keep the UTM behavior intact where desired.

Do not globally delete the VM's boot-splash implementation unless the user specifically requests it.

For the S10+ runtime:

**ONE BOOT ANIMATION, ONE TRANSITION, ONE LAUNCHER.**

Verify no second fullscreen video remains active after startup.

---

# 10. CRITICAL ISSUE — A30 FRAMEBUFFER OWNERSHIP

A30's bridge source identifies the measured conflict:

`/opt/nuxel/nuxel-anim-player`

and:

`/usr/lib/nuxel/nuxel-wl-fb`

were simultaneously writing to the same framebuffer.

That directly explains why animation frames could alternate with launcher frames.

A30 introduced new handoff logic, but the current code still requires a full review.

## 10.1 Verify what is actually deployed

The presence of an A30 binary in the build directory is not evidence that it is the currently running binary.

Determine:

- Installed bridge SHA-256.
- Source revision.
- Active process executable path.
- Running command line.
- Active service version.
- Animation process identity.
- Framebuffer ownership.
- Installed handoff logic.

Compare deployed source/binary against A30.

Do not rebuild blindly before identifying the deployed version.

## 10.2 Correct handoff ordering

The required transition is:

`BOOT_ANIMATION_OWNER`

→ `WEBKIT_PWA_LOADED`

→ `PWA_FIRST_FRAME_AVAILABLE`

→ `ANIMATION_STOP_REQUESTED`

→ `ANIMATION_STOP_ACKNOWLEDGED`

→ `WAYLAND_FRAMEBUFFER_BRIDGE_OWNER`

→ `LAUNCHER_VISIBLE`

The implementation must never allow two processes to concurrently write scanout memory.

The A30 source currently stages a launcher frame and can perform a blit while the animation stop is still pending.

Review whether that defeats exclusive ownership.

**Never mark the bridge as exclusive owner solely because a stop request was sent.**

Require proof of actual termination or an explicit relinquished-ownership acknowledgment.

## 10.3 Fix the timeout behavior

The existing A30 code has an animation-stop timeout and may continue even if the old painter remains alive.

This is unsafe for the desired ownership guarantees.

If stop confirmation fails:

- Do not blindly claim ownership.
- Do not race the still-running animation.
- Record the specific failure.
- Attempt a bounded, identity-verified recovery.
- Preserve a visible diagnostic fallback.
- Avoid breaking the AMOLED or live console.

Do not blindly kill PIDs from stale files.

Verify process identity using actual executable/cmdline and process lifetime.

## 10.4 Fix repeated framebuffer reassertions

Review the current bridge's periodic use of:

`FBIOPUT_VSCREENINFO`

`FBIOPAN_DISPLAY`

and its panel-reassertion logic.

The bridge should not unnecessarily reset display state on every reporting interval.

Determine whether repeated settings writes contribute to flicker, blanking or frame instability.

Measure actual driver behavior and return codes.

Prefer one-time initialization and normal frame presentation.

Retain exceptional panel recovery only when real failure evidence justifies it.

Do not disable legitimate safety or power controls.

## 10.5 Limit rendering load

Previous A29 logs reported extremely high bridge frame counts.

That does not prove the AMOLED is physically refreshing at that rate.

Measure:

- Compositor frame rate.
- Screencopy frame rate.
- Actual framebuffer writes.
- CPU use.
- Memory use.
- Frame timing.
- Number of failed captures.
- Page-panning behavior.

Implement bounded, paced presentation.

Start from a stable 30 FPS target, evaluate 60 FPS if performance supports it.

Do not let a tight screencopy loop consume excessive CPU or power without improving visible output.

**P4 ACCEPTANCE: NO CONCURRENT FRAMEBUFFER WRITERS, NO UNCONTROLLED FLICKERING, NO ANIMATION BLEED-THROUGH.**

---

# 11. CRITICAL ISSUE — TOUCHSCREEN HARDWARE IS NOT THE ONLY BLOCKER

The user still cannot operate the launcher by touch.

Do not start from the assumption that the touchscreen is physically dead.

The A29b record shows that the kernel has successfully produced actual touch data under the correct conditions.

Evidence previously recorded:

- sec_ts IRQ counts increased.
- Physical touch-count register changed.
- Kernel reported contact press and release.
- The userspace reader received `TOUCH_POINT`.
- Phoc/libinput opened event devices.

That is important evidence, but it does not prove the CURRENT runtime remains in the same state.

## 11.1 Determine the current input failure stage

Check in order:

1. Normal boot mode, not charger mode.
2. Samsung `sec_touchscreen` input device registered.
3. IRQ counter changes during physical touch.
4. Evdev emits the appropriate events.
5. libinput receives the events.
6. Phoc maps the touchscreen to the correct output.
7. Phoc delivers Wayland pointer/touch events.
8. WebKit receives touch/pointer events.
9. The PWA launcher receives those events.
10. Application activation callbacks fire.

**DO NOT STOP AT STEP 4 AND CLAIM THE TOUCHSCREEN IS FIXED.**

The end goal is actual launcher interaction.

## 11.2 A29b charger-mode finding

The A29b record found that charger-mode boots prevented touchscreen initialization entirely.

Evidence:

`androidboot.mode=charger`

`lpcharge=1`

`sec_ts_init` did not bind the touchscreen.

A normal OS reboot previously cleared that mode.

Check current `/proc/cmdline`.

Do not try to recover a nonexistent device by changing userspace input handlers.

If the phone is in charger mode, explain the condition and use a controlled normal-boot path when appropriate.

## 11.3 A29b driver power-state finding

The downstream Samsung driver sometimes returns early from:

`sec_ts_start_device()`

because `power_status` already indicates `POWER_ON`, preventing the IRQ from being enabled.

A29 introduced:

`nuxel-touch-arm`

The source uses Samsung's existing touch control mechanisms and a display notifier sequence to arm the controller.

Verify its present operation.

Inspect:

`/run/nuxel-touch-arm.state`

`/proc/interrupts`

`/sys/class/sec/tsp/`

Kernel messages.

A29b measured that an explicit `module_on_master` command could leave the controller unable to read.

Do not reintroduce that broken sequence.

## 11.4 Avoid repeated display blanking

The touch-arm helper can write to:

`/sys/class/graphics/fb0/blank`

to trigger a panel notifier.

That procedure must not run repeatedly while the launcher is active merely to keep the touchscreen alive.

Such operations can produce visual blanking or interfere with the animation handoff.

If arming is required, perform it once at the correct startup stage where possible.

Verify that the controller remains active afterward.

If a durable, correct driver-state fix is eventually needed, isolate it for a future kernel maintenance cycle.

Do not casually patch live kernel memory or manipulate raw hardware registers.

## 11.5 Confirm the actual physical touch path

Run a bounded touch test.

Have the user tap the screen and swipe once while capture is active.

Record:

- IRQ delta.
- Evdev events.
- libinput events.
- Phoc events.
- WebKit pointer/touch events.
- PWA click-handler invocation.

Use unique timestamps or tracing IDs to correlate one physical touch through each layer.

The target is to find the first layer where a real touch disappears.

This is much more informative than repeating a raw touch reader that already worked.

---

# 12. CONNECT PHYSICAL TOUCH TO THE ACTUAL WEBKIT LAUNCHER

The launcher uses browser events.

Inspect:

`pwa/nuxel-home/js/launcher.js`

Its handlers include pointer/touch interactions.

Verify:

- Pointerdown.
- Pointermove.
- Pointerup.
- Touchstart.
- Touchend.
- Click synthesis.
- Long press.
- App tile hit testing.
- Search focus.
- Scrolling.
- Window focus.

Determine whether the WebKit window is receiving the actual Wayland touch events.

Check whether:

- The compositor's output transform is incorrect.
- The touchscreen is mapped to a different output.
- The window lacks keyboard/pointer focus.
- libinput sees a device but does not associate it with the session.
- Seat permissions are wrong.
- Touch is being swallowed by another layer.
- A transparent or fullscreen overlay intercepts input.
- The lingering boot-splash element remains above the launcher.
- WebKit incorrectly treats the input as pointer-only.
- Touch coordinates don't match the 720×1520 Wayland output.

Important: the old fullscreen PWA boot-splash overlay could be affecting both visual appearance and input delivery.

Check its computed state and pointer-events behavior.

Do not guess which layer is responsible.

Use logging instrumentation if necessary.

**TOUCH SUCCESS = USER TAPS THE REAL PWA APP GRID AND THE SELECTED APPLICATION OPENS.**

---

# 13. THE WAYLAND OUTPUT GEOMETRY MUST BE CORRECT

The VM uses a virtual display around:

`720 × 1440`

with scale 2.

The Samsung uses a physical framebuffer around:

`1440 × 3040`

A29 configured a headless Wayland output and a framebuffer bridge.

Verify:

- Phoc output dimensions.
- WebKit viewport size.
- CSS logical width.
- Wayland output scale.
- Physical pixel mapping.
- Touchscreen raw X/Y range.
- Output transform.
- Rotation.
- Safe area for the punch-hole camera.

Do not assume that visually rotating a phone or photographing it sideways means the UI's coordinate system is wrong.

Determine actual device and compositor transformations.

The launcher should use portrait as its normal home orientation, with correct physical touch mapping.

If automatic rotation is unavailable, provide a stable manual orientation setting.

Do not stretch or rotate only the graphics while leaving input unmapped.

---

# 14. CRITICAL ISSUE — APPLICATION BRIDGE INCOMPLETE

A29b confirmed the actual launcher can load through WebKitGTK, but noted that application activation was not fully proven.

The source uses:

`pwa/nuxel-home/js/apps.js`

`pwa/nuxel-home/js/app.js`

`pwa/nuxel-common/bridge.js`

The original VM includes:

`nuxel-http-bridge`

and other Nuxel services.

Previous phone logs recorded bridge/API token requests failing.

Investigate:

- Whether `nuxel-http-bridge.service` is installed.
- Whether it starts correctly.
- Which port/interface it binds.
- Whether the launcher can reach it.
- Token generation.
- Authentication.
- Allowed origins.
- Required D-Bus services.
- Native application activation.
- Custom `nuxel-...://` handlers.
- PWA application URLs.
- Actual PWA app loading.

Do not merely add icons.

The launcher must activate available applications through the existing Nuxel system.

Use the working UTM VM to identify the real bridge configuration.

Bring over the same behavior where it is compatible.

Keep the bridge local to the handset and enforce appropriate authentication.

Do not introduce an unrestricted unauthenticated command-execution API.

## Application acceptance

Test the actual launcher registry.

For each entry:

- App exists.
- Icon loads.
- Launch handler resolves.
- Backend is available.
- Activation succeeds or produces a truthful unsupported result.
- Return-to-home works.

Do not invent dummy success responses for unavailable telephony, camera or modem hardware.

Nuxel beta can have unsupported hardware features, but they must be accurately represented.

---

# 15. SECONDARY ISSUE — WEBKIT MEDIA AND PROCESS STABILITY

A29b also found WebKit web-process crashes associated with missing GStreamer audio sink plugins.

The phone had incomplete media dependencies compared with the VM.

A29 modified `nuxel-pwa-host.c` to disable media when the required sink is absent.

Verify that implementation in the active runtime.

Ensure:

- WebKit does not crash.
- Launcher loads completely.
- The redundant boot video does not start in the phone runtime.
- Missing media plugins do not crash the whole launcher.
- Browser subprocess failures are supervised.
- A crashed WebKit process is detected and restarted.
- The phone falls back to a known working interface if WebKit repeatedly fails.

Do not disable every WebKit feature globally merely to hide dependency problems.

Preserve the existing launcher's normal web functionality.

---

# 16. BETA SECURITY AND ROBUSTNESS REVIEW

Before promoting Nuxel from alpha to beta, inspect obvious development-only shortcuts.

Particular areas:

## WebKit permissions

Review:

`tools/s10plus/a29/nuxel-pwa-host.c`

Its current permission handler appears to automatically allow permission requests.

Replace blanket permission grants with an explicit, capability-aware policy appropriate to the application and device.

Do not automatically grant sensitive permissions to arbitrary pages.

## HTTP bridge

Restrict the bridge to intended local access.

Validate caller identity and origin.

Protect privileged operations.

## Live console

Preserve the user's trusted USB development access.

Ensure no additional unauthorized network exposure is introduced during this mission.

## Deployment

Require exact hash verification, atomic replacement and rollback.

## Service restarts

Apply bounded restart policies to avoid process storms or battery drain.

## Display

Avoid runaway rendering loops and repeated panel initialization.

## Touchscreen

Avoid repeated power-state transitions after startup.

This is not a request to change unrelated user-selected network bindings or restrict explicitly authorized LAN services. Scope changes to defects and risky development shortcuts found in this phone integration.

---

# 17. BETA QUALITY GATES

Define measurable beta acceptance.

## Gate A — Original launcher

The physical handset runs the actual `pwa/nuxel-home/` code through the verified WebKitGTK/Wayland path.

The expected app registry, CSS and JavaScript are loaded.

No A27/A28 substitute frontend is being presented as the final launcher.

## Gate B — Wallpaper

`assets/nuxel-background.png` is installed and served at the correct path.

Its CSS background is applied on the actual launcher.

The user confirms it visually.

## Gate C — Touch

Actual physical touch enters sec_ts, evdev, libinput, Phoc, WebKit and the PWA.

Tap and swipe navigation work.

App selection works.

## Gate D — Animation

Exactly one OS boot animation owns the framebuffer at a time.

No second PWA startup video obscures the launcher.

The bridge takes ownership only after valid readiness and stop acknowledgment.

No concurrent painter remains.

## Gate E — Applications

Available applications launch through the real Nuxel application registry and bridge.

Unavailable hardware-dependent features have accurate status reporting.

## Gate F — Runtime

Fedora remains stable.

No uncontrolled watchdog resets.

No repeated WebKit crashes.

No unbounded renderer CPU usage.

USB console remains usable.

## Gate G — Reboot persistence

All source fixes are installed through the reproducible rootfs builder.

A controlled normal reboot returns to the correct launcher with its wallpaper and working input.

Do not reboot until live testing has passed and a recovery plan is available.

## Gate H — Recovery

Maintain a known-working fallback UI and recovery mechanism.

No unverified flash operations.

---

# 18. AUTOMATED TESTING

Build a regression suite with deterministic tests.

Tests must not depend on interpreting screenshots.

Required test categories:

- Correct launcher URL.
- Correct app registry.
- Correct asset paths.
- Wallpaper HTTP response.
- CSS loading.
- JavaScript loading.
- Service worker cache validity.
- WebKit load completion.
- WebKit subprocess survival.
- HTTP bridge authentication.
- App activation.
- Touch event propagation.
- Coordinate mapping.
- Animation stop signaling.
- Painter process termination.
- Exclusive framebuffer ownership.
- Display-driver ioctl behavior.
- Frame timing.
- Service restart behavior.
- Live-console reconnect.
- Binary transfer integrity.
- Application rollback.
- Boot persistence.

All tests must report actual exit codes.

For display and touch acceptance, the user will provide final physical confirmation.

Do not claim physical visual correctness solely from a software marker.

---

# 19. LIVE DEPLOYMENT RULES

For each userspace change:

1. Record source revision.
2. Build the affected ARM64 component.
3. Run offline tests.
4. Capture previous installed hash.
5. Preserve working version.
6. Transfer through verified USB console.
7. Compare target SHA-256.
8. Atomically install.
9. Restart the smallest affected service.
10. Verify the service remains active.
11. Verify the console remains alive.
12. Validate the intended behavior.
13. Roll back on failure.

The A29 records found that long command lines could be silently truncated by the console.

Use the proven chunked transfer mechanism where needed.

Do not assume large base64 payloads can be pasted safely into a serial shell.

Do not issue several simultaneous serial commands through competing host processes.

All changes must also be reflected in the repository's release/build scripts.

---

# 20. DOCUMENTATION AND DELIVERABLES

Continue maintaining:

`docs/s10plus-autonomous-boot-repair/`

Create:

`docs/s10plus-autonomous-boot-repair/BETA-FINALIZER/`

Files:

- `00-CURRENT-STATE.md`
- `01-VM-LAUNCHER-RUNTIME.md`
- `02-S10PLUS-LAUNCHER-RUNTIME.md`
- `03-LAUNCHER-ROOT-CAUSE.md`
- `04-WALLPAPER-ROOT-CAUSE.md`
- `05-ANIMATION-FLICKER-ROOT-CAUSE.md`
- `06-FRAMEBUFFER-OWNERSHIP.md`
- `07-TOUCHSCREEN-END-TO-END.md`
- `08-WEBKIT-BRIDGE-AND-APPS.md`
- `09-LIVE-DEPLOYMENTS.md`
- `10-BETA-TEST-RESULTS.md`
- `11-BETA-RELEASE-NOTES.md`
- `12-REMAINING-LIMITATIONS.md`

Also create an actionable beta acceptance checklist.

Distinguish:

- Source fixed.
- Offline tested.
- Deployed.
- Observed running.
- Physically validated.
- Still blocked.

Do not invent results or optimistic percentages.

---

# 21. EXACT EXECUTION ORDER

**START NOW WITH BOTH THE UTM VM AND THE PHYSICAL NUXEL S10+ RUNNING.**

## PHASE 1 — THE REAL LAUNCHER

1. Connect to the UTM VM.
2. Inspect the exact running launcher process.
3. Identify its executable, URL, dependencies and service configuration.
4. Connect to the physical S10+ live console.
5. Inspect its active launcher processes.
6. Verify the WebKitGTK PWA host.
7. Verify the complete launcher URL and PWA document tree.
8. Check CSS/JS/module HTTP requests.
9. Identify whether the A27 fallback is still active.
10. Correct service selection and startup.
11. Ensure the real Nuxel PWA is displayed.
12. Prevent competing launcher processes.

## PHASE 2 — WALLPAPER

13. Verify the existing repo wallpaper.
14. Fix the broken PWA asset path.
15. Deploy the original wallpaper.
16. Verify HTTP 200 and correct MIME type.
17. Verify the CSS references it.
18. Correct cache/version behavior if required.
19. Confirm static wallpaper ownership by the launcher.

## PHASE 3 — TOUCHSCREEN

20. Verify normal boot mode.
21. Inspect sec_ts controller state.
22. Inspect the touch-arm service.
23. Verify physical IRQ activity.
24. Verify evdev events.
25. Verify libinput receives events.
26. Verify Phoc output and seat mapping.
27. Verify WebKit pointer/touch events.
28. Verify PWA click handlers.
29. Fix the first stage where events disappear.
30. Test physical app selection and swipe navigation.

## PHASE 4 — ANIMATION AND DISPLAY

31. Identify all framebuffer writers.
32. Verify actual deployed A30 bridge version.
33. Fix exclusive ownership before first output.
34. Require true animation-stop acknowledgment.
35. Eliminate the second PWA video overlay on the phone.
36. Review periodic framebuffer reassertions.
37. Fix unnecessary blank/unblank transitions.
38. Pace frame capture and presentation.
39. Verify no animation frames remain visible after launcher takeover.
40. Verify no renderer collision or panel reset.

## PHASE 5 — BETA INTEGRATION

41. Fix WebKit media/backend errors.
42. Restore Nuxel HTTP bridge/API behavior.
43. Verify actual application launching.
44. Review relevant permissions and service boundaries.
45. Verify stable CPU/memory behavior.
46. Exercise launcher and touch repeatedly.
47. Preserve working deployment and rollback.
48. Integrate fixes into the Fedora rootfs builder.
49. Run offline and live regression tests.
50. Perform one controlled normal reboot only when justified and safe.
51. Verify launcher, wallpaper, animation and touch survive reboot.
52. Produce beta release notes and remaining blocker list.

Do not stop merely because the launcher URL loads.

Do not stop merely because the wallpaper file exists.

Do not stop merely because sec_ts registers.

Do not stop merely because the animation reports STOPPED.

Every milestone requires the corresponding end-to-end behavior.

---

# 22. STOP AND ESCALATION RULES

If a userspace fix does not work:

- Preserve console access.
- Collect the actual error.
- Revert the failed deployment.
- Investigate the cause.
- Continue with a smaller correction.

If a driver requires a genuine kernel change:

- Record the exact defect.
- Prepare source patches and offline tests.
- Do not attempt live kernel/BOOT rewriting.
- Preserve the proven kernel.
- Separate the future BOOT update from this live beta mission.

If the compositor fails repeatedly:

- Restore the known-working framebuffer fallback.
- Keep the USB console accessible.
- Do not force endless restart loops.

If the touchscreen fails to emit events:

- Determine whether the failure is charger mode, sec_ts driver state, IRQ delivery or input handling.
- Do not manufacture synthetic events and call touch fixed.

If the user cannot perform a physical test immediately:

- Continue other safe engineering work.
- Record that hardware acceptance remains pending.

---

# 23. FINAL BETA DEFINITION

The device may be called:

**NUXEL S10+ BETA 0.1**

only after proving:

- Original UTM Nuxel Home PWA is running.
- Correct Nuxel wallpaper.
- Original animation ends cleanly.
- No sustained screen flicker.
- Physical touchscreen drives the launcher.
- Available applications actually open.
- Fedora remains stable.
- USB diagnostics remain accessible.
- Application/system changes survive a normal reboot.
- Recovery remains possible.

Beta does NOT mean all smartphone hardware is necessarily complete.

Track telephony, cellular data, Wi-Fi, audio, camera, sensors, suspend/resume and battery life separately.

Do not claim daily-driver readiness without testing those components.

---

# FINAL DIRECTIVE

WE ALREADY BUILT THE LAUNCHER.

WE ALREADY HAVE THE WALLPAPER.

WE ALREADY HAVE THE BOOT ANIMATION.

WE ALREADY HAVE THE TOUCHSCREEN DRIVER PRODUCING PHYSICAL DATA IN A29b.

WE ALREADY HAVE THE WAYLAND-TO-FRAMEBUFFER BRIDGE.

**STOP CREATING NEW FRONTS FOR THE SAME COMPONENTS.**

MAKE THE EXISTING SYSTEM WORK TOGETHER.

**ONE LAUNCHER.**

**ONE WALLPAPER.**

**ONE FRAMEBUFFER OWNER.**

**ONE CLEAN BOOT ANIMATION.**

**ONE WORKING TOUCHSCREEN.**

**REAL APPLICATIONS.**

**REAL FEDORA.**

## NUXEL BETA MISSION

SAMSUNG BOOTS

→ ORIGINAL NUXEL ANIMATION

→ ANIMATION STOPS CLEANLY

→ REAL UTM NUXEL HOME APPEARS

→ STATIC NUXEL WALLPAPER

→ FINGER TAP OPENS AN APPLICATION

→ NUXEL REMAINS STABLE

**DO IT ALL LIVE THROUGH THE NUXEL CONSOLE WHERE TECHNICALLY POSSIBLE.**

NO IMAGE ANALYSIS.

NO NEW LAUNCHER.

NO UNNECESSARY TWRP.

NO UNVERIFIED SUCCESS CLAIMS.

**TAKE NUXEL FROM ALPHA TO BETA.**

🐧🔥 EXECUTE THE BETA FINALIZER MISSION.
