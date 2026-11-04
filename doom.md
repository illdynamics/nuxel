# NUXEL-A76 — OPERATION DOOM POCKET PWNAGE 25000
## Build the ultimate mobile-first DOOM experience for Nuxel Linux

**Mission:** Transform Nuxel into a proper mobile gaming platform by integrating a fully playable, touchscreen-optimized DOOM experience. This is not a simple desktop port. Build a first-class native Linux phone game experience with custom controls, launcher, engine integration, Flatpak distribution, haptics and performance optimization.

**Repository:** `github.com/illdynamics/nuxel`  
**Primary hardware target:** Samsung Galaxy S10+ (`beyond2lte`, Exynos 9820, aarch64)  
**Operating system:** Current Nuxel Fedora-based build  
**Distribution:** Native Nuxel Flatpak application  
**App identity target:** `org.nuxel.Doom` (verify naming conventions before adopting)  
**Campaign:** Freedoom as the freely distributable default game content.

---

# 1. ROLE AND EXECUTION REQUIREMENTS

You are the autonomous principal Linux mobile gaming engineer, GTK4/libadwaita developer, SDL2 engine developer, ARM64 performance engineer and Nuxel systems integrator.

Your mission is to IMPLEMENT, BUILD, TEST AND DOCUMENT the complete solution.

Do not stop after producing a research report, architecture proposal or implementation plan.

Execute the entire task in the existing repository.

Work methodically and independently. Resolve technical issues instead of documenting them as excuses.

Critical rules:

- Inspect the actual current repository before modifying anything.
- Preserve all unrelated working functionality.
- Respect existing architectural conventions and security boundaries.
- Do not replace the existing launcher, compositor, navigation system or display management.
- No Android dependencies, emulation or compatibility layers.
- No Snap.
- No proprietary game assets bundled into the distribution.
- No unnecessary network access.
- No privileged input injection.
- No destructive device operations.
- Never flash a phone, erase data or reboot hardware as part of this task.

Inspect the current working tree and preserve existing uncommitted changes. Do not reset or overwrite unrelated user work.

If an assumption in this prompt conflicts with the current implementation, investigate and follow the actual source of truth.

---

# 2. PHASE ZERO — REPOSITORY AND HARDWARE RECONNAISSANCE

Before writing code, inspect:

- README.md
- CHANGELOG.md
- VERSION
- Latest NUXEL-A75 prompt and previous relevant prompt history
- docs/app-store.md
- docs/pwa-model.md
- Current NuXtore implementation
- Nuxel Home and launcher implementation
- Flatpak manifests and runtime configuration
- Application discovery and registration
- Nuxel permission and sandbox systems
- Nuxel Portal and Bridge D-Bus interfaces
- Orientation and rotation management
- Navigation: Back / Home / Tabs
- Haptics services
- PipeWire audio integration
- Application lifecycle and suspension
- Current S10+ display bridge and Phoc implementation
- Existing application icons and asset conventions
- Build scripts, CI and VM testing infrastructure.

Determine the real application launch contract, foreground lifecycle, app discovery mechanism and Flatpak installation model.

**Hardware reality:**

The S10+ implementation has historically used a DECON framebuffer screencopy bridge and headless Phoc. Do not assume that an SDL application can directly access DRM/KMS, GBM or `/dev/dri`.

Determine the actual SDL2 video driver and Wayland presentation path available in the current build.

Test the real rendering and input path rather than merely verifying that the engine executable starts.

Produce a concise initial technical assessment and immediately proceed with implementation.

# 3. PHASE ONE — CHOOSE AND INTEGRATE THE DOOM ENGINE

Evaluate these projects:

1. Chocolate Doom: https://github.com/chocolate-doom/chocolate-doom
2. Crispy Doom: https://github.com/fabiangreffrath/crispy-doom
3. Other lightweight, actively maintained SDL2-compatible source ports if there is a compelling technical reason.

Chocolate Doom is an excellent baseline because of its lightweight implementation and historically faithful gameplay.

Crispy Doom should be evaluated for its improved rendering and additional gameplay features.

Selection criteria:

- Native ARM64 compatibility.
- SDL2 support.
- Wayland compatibility.
- Good performance on Exynos 9820.
- Reasonable memory consumption.
- Open-source implementation.
- Reproducible build.
- Sustainable upstream maintenance.
- Feasible native touchscreen integration.

Do not simply download an unverified binary.

Pin an upstream version or commit and verify downloaded source checksums.

Prefer maintaining a small, clearly documented Nuxel-specific patch set over creating an unnecessarily large proprietary fork.

The engine must support:

- Original DOOM-compatible WAD files.
- Freedoom.
- Savegames.
- Audio.
- Configurable rendering.
- Keyboard input.
- Bluetooth game controllers.
- Custom touch input.

Use a native SDL2 engine for the gameplay itself. A GTK4 application should provide the Nuxel-facing launcher and configuration experience.

# 4. PHASE TWO — BUILD THE MOBILE-FIRST DOOM APPLICATION

Create a proper Nuxel application.

The target experience:

A user opens NuXtore, taps DOOM, installs it, launches it and immediately has a playable game without needing a keyboard, mouse or terminal.

Application screens:

### A. DOOM home screen

Create a retro arcade-inspired Nuxel interface.

Include:

- Large PLAY DOOM button.
- Campaign selection.
- Installed game data indicator.
- Engine version.
- Performance mode.
- Touch control settings.
- Controller settings.
- Sound and haptics settings.
- Import WAD option.
- About and license information.

Visual direction:

- Nuxel's existing pixel-art aesthetic.
- Dark arcade-inspired interface.
- Crisp retro typography.
- Limited glow and transparency.
- Properly sized touchscreen controls.
- Original Nuxel DOOM graphics and icons.

Create a dedicated DOOM application icon featuring a Nuxel-inspired retro gaming penguin/space marine. Do not copy copyrighted DOOM artwork.

### B. Game launcher

The PLAY button must:

1. Validate that a compatible IWAD exists.
2. Select the configured campaign.
3. Acquire the existing Nuxel landscape orientation mechanism where supported.
4. Start the engine.
5. Initialize the configured touch HUD.
6. Initialize audio and optional haptics.
7. Enter gameplay.

Handle engine startup failures gracefully.

Provide useful error messages instead of silently crashing.

### C. Campaign selection

Implement:

- Freedoom Phase 1.
- Freedoom Phase 2.
- FreeDM where supported.
- User-imported DOOM and DOOM II IWADs.

Do not bundle copyrighted commercial WAD files.

Freedoom is game content rather than an engine: https://github.com/freedoom/freedoom

Verify its current redistribution conditions before bundling any assets.

Prefer including a verified, pinned, freely distributable Freedoom release with its required license files, provided the build and distribution conditions permit it.

Otherwise implement an opt-in, checksum-verified installation or import flow.

The user must be able to import legally obtained WAD files using the existing XDG document portal.

Never grant unrestricted home-directory access merely to locate game files.

Copy imported content into the application's private persistent storage and validate its format before enabling it.

---

# 5. PHASE THREE — THE TOUCHSCREEN DOOM CONTROL SYSTEM

THIS IS THE MOST IMPORTANT PART OF THE PROJECT.

The game must be genuinely playable using only the phone touchscreen.

A stock desktop Doom interface is not an acceptable result.

Implement a mobile touchscreen HUD integrated into the actual SDL2 game rendering/input process.

Investigate the SDL2 event architecture and implement native SDL multitouch support.

Prefer intercepting SDL_FINGERDOWN, SDL_FINGERMOTION and SDL_FINGERUP inside the engine process, translating touch gestures into the engine's native movement, mouse-look and action inputs.

Draw the controls as an overlay in the game viewport.

Do not implement an external privileged keyboard injector, unrestricted uinput daemon or global touch interception service.

## A. Default landscape control layout

Create a layout similar to a modern mobile FPS.

**LEFT SIDE — MOVEMENT**

A virtual analog joystick with:

- Forward.
- Backward.
- Strafe left.
- Strafe right.
- Diagonal movement.
- Configurable sensitivity.
- Configurable dead zone.

The joystick must support both fixed and floating modes.

**RIGHT SIDE — AIMING**

A dedicated touch-look area.

- Drag horizontally to turn.
- Drag vertically for configurable look movement where supported.
- Configurable sensitivity.
- Adjustable response curve.
- Optional inverted Y-axis.
- Smooth movement without excessive latency.

**RIGHT THUMB BUTTONS**

Large touchscreen actions:

- FIRE.
- USE / OPEN DOOR.
- WEAPON NEXT.
- WEAPON PREVIOUS.
- PAUSE / MENU.
- RUN.

Optional secondary controls:

- Quick weapon selection.
- Automap.
- Menu.
- Screenshot.

Use engine-supported features and do not invent bindings that do not exist.

## B. Multitouch support

Allow simultaneous actions.

Examples:

- Move forward while aiming.
- Strafe while shooting.
- Turn while firing.
- Move while activating doors.

Track individual SDL touch/finger IDs.

Maintain correct button-down and button-up semantics.

Handle:

- Finger cancellation.
- Focus loss.
- Rotation.
- Application suspension.
- Pause.
- Engine termination.

Never leave a movement or firing key stuck after a finger disappears.

## C. HUD appearance

Create an attractive retro gaming HUD.

Controls must be:

- Large enough for thumbs.
- Responsive to different screen dimensions.
- Properly spaced.
- Semi-transparent but readable.
- High contrast.
- Configurable.
- Able to avoid important gameplay HUD areas.

Provide at least two layouts:

1. Standard right-handed layout.
2. Left-handed layout.

Allow adjustable:

- Button size.
- HUD opacity.
- Joystick size.
- Joystick sensitivity.
- Look sensitivity.
- Button positioning.
- HUD visibility.

Persist all preferences across restarts.

Do not hardcode coordinates for one specific resolution.

Use current runtime display dimensions and safe-area information.

## D. Physical controllers

Preserve native keyboard and mouse support.

Support SDL-compatible Bluetooth game controllers where available.

The touchscreen HUD and physical gamepad must coexist without fighting over input state.

Automatically recognize controller connection and disconnection.

Provide a controller configuration page.

---

# 6. PHASE FOUR — LANDSCAPE, FULLSCREEN AND NAVIGATION

DOOM should feel like a proper handheld gaming application.

Use Nuxel's existing orientation management.

Request landscape mode only while gameplay requires it.

Important:

- Do not issue arbitrary wlr-randr commands from the application.
- Do not directly manipulate the framebuffer.
- Do not modify the kernel display configuration.
- Do not permanently alter system orientation.
- Do not circumvent the Nuxel Portal.
- Do not break existing orientation restoration.

Use an existing supported orientation API or introduce a narrowly scoped, capability-controlled orientation lease if necessary.

When the game exits, restore the previous display orientation.

If the engine crashes or the app is terminated, do not leave the phone trapped in landscape mode.

Preserve Nuxel's three-button navigation:

**BACK:** Pause the game or return from an in-game menu.

**HOME:** Always return to Nuxel Home using the existing navigation mechanism.

**TABS:** Open the existing application overview.

Never intercept or disable the system HOME action.

Implement a proper pause screen containing:

- Resume.
- Controls.
- Sound settings.
- Save game.
- Load game.
- Restart level.
- Return to campaign.
- Exit DOOM.

Pause automatically when the application loses foreground focus.

Resume safely without stale touch states.

The game must not interfere with the existing app switcher or background application management.

# 7. PHASE FIVE — AUDIO, HAPTICS AND PERFORMANCE

## Audio

Integrate through the existing Nuxel PipeWire audio setup.

Support:

- Weapon sounds.
- Enemy sounds.
- Music.
- Menu sounds.
- Configurable sound volume.
- Configurable music volume.

Do not replace Nuxel's audio server or create another competing audio service.

Handle audio focus and app suspension properly.

Verify that gameplay audio is actually audible through the S10+ speaker route.

## Haptics

Integrate with the existing Nuxel haptics service.

Implement optional subtle vibration for:

- Weapon firing.
- Damage received.
- Explosion events where technically appropriate.
- Menu interactions.

Use throttling and intensity controls.

Do not send one vibration request per render frame.

Haptics must be optional and must gracefully degrade when unavailable.

## Performance

The S10+ is a mobile device, not a gaming PC.

Optimize for ARM64 and the Exynos 9820.

Implement:

- Configurable rendering resolution.
- Pixel-perfect scaling.
- Optional reduced-resolution mode.
- 30 FPS battery saver.
- 60 FPS performance target.
- Configurable frame pacing.
- Efficient software rendering.
- Minimal background allocations.
- Avoidance of unnecessary GTK rendering while gameplay is active.

Do not assume a working DRM acceleration path.

Do not force llvmpipe or CPU rendering when an existing working GPU-backed presentation path is available.

Measure actual performance.

Target stable 30 FPS minimum and 60 FPS where achievable.

Provide a low-performance mode for devices with weaker graphics hardware.

Avoid thermal and battery drain caused by unnecessary uncapped rendering.

# 8. PHASE SIX — FLATPAK AND NUXEL DISTRIBUTION

Package the complete application according to Nuxel's actual distribution architecture.

The final product should be installable through NuXtore.

Implement:

- Flatpak manifest.
- Reproducible build instructions.
- ARM64 support.
- Proper application ID.
- Desktop entry.
- AppStream metadata.
- Application icon.
- Version metadata.
- License files.
- Source repository reference.
- Nuxel permission metadata.
- Persistent app-specific storage.
- Proper uninstall integration.

Use the project's established GNOME runtime and org.nuxel.Platform conventions where appropriate.

Do not blindly assume that every existing application uses the same runtime.

Inspect the current manifests before making that decision.

Keep permissions minimal.

Expected permissions should be limited to actual requirements:

- Display access through the established Wayland mechanism.
- Audio output.
- Game controller access when needed.
- XDG document portal for user-imported WAD files.
- Required session services.

No network access by default.

No broad filesystem permissions.

No unrestricted device access.

No unnecessary system bus permissions.

The game should remain completely playable offline after installation.

Integrate with the actual NuXtore application discovery and installation workflow.

Ensure that installation detection, launch, upgrades and uninstall all function correctly.

Do not merely add an icon to the launcher without a functioning installed application behind it.

# 9. PHASE SEVEN — QUALITY ASSURANCE

Build a comprehensive automated test suite.

## Engine tests

- ARM64 compilation.
- SDL2 initialization.
- Wayland startup.
- Fullscreen behavior.
- IWAD discovery.
- WAD validation.
- Save/load.
- Audio initialization.
- Controller detection.

## Touch-input tests

Test:

- Single-finger movement.
- Single-finger aiming.
- Fire button.
- Simultaneous movement and fire.
- Simultaneous movement and aiming.
- Simultaneous movement, aiming and fire.
- Finger cancellation.
- Focus loss.
- Application suspension.
- Rotation.
- Repeated pause/resume.

Verify that all input states are released correctly.

## Nuxel integration tests

- Application appears in NuXtore.
- Application installs.
- Application launches from Nuxel Home.
- Application enters landscape safely.
- HOME works during gameplay.
- TABS works during gameplay.
- BACK opens the pause menu.
- Engine exits cleanly.
- Orientation restores.
- Audio route restores.
- Haptics can be disabled.
- Application survives normal suspension/resume.
- Existing applications continue functioning.

## Performance tests

Record:

- Memory consumption.
- CPU utilization.
- Frame rate.
- Frame-time stability.
- Startup time.
- Audio latency.
- Touch response latency.

Test normal and reduced-resolution rendering.

Use a VM and automated tests where possible.

Use actual S10+ test results where hardware is available.

Do not claim a physical-device test passed unless it was genuinely performed.

# 10. PHASE EIGHT — DOCUMENTATION AND RELEASE READINESS

Create:

- `docs/games/doom.md`
- `docs/games/doom-touch-controls.md`
- `docs/games/doom-troubleshooting.md`
- Flatpak build and installation documentation.
- WAD import instructions.
- Controller pairing instructions.
- Performance tuning documentation.
- License and redistribution documentation.

Add a changelog entry.

Update application and feature documentation.

Create an implementation report documenting:

1. Selected engine and why.
2. ARM64 compatibility.
3. Touchscreen implementation.
4. Fullscreen and orientation integration.
5. Audio and haptics.
6. Flatpak permissions.
7. NuXtore integration.
8. Tests performed.
9. Actual performance measurements.
10. Known remaining limitations.

Keep version numbers consistent with the current repository conventions. Do not arbitrarily bump the OS release version for an individual application.

# 11. FINAL ACCEPTANCE CRITERIA

The project is NOT COMPLETE merely because a DOOM executable compiles.

All of the following are required for completion:

| Requirement | Expected result |
|---|---|
| Native engine | ARM64 SDL2 engine builds |
| Mobile launcher | Native Nuxel application |
| Flatpak | Installable package |
| NuXtore | Discoverable and launchable |
| Game content | Freedoom or imported IWAD |
| Touch movement | Working |
| Touch aiming | Working |
| Touch shooting | Working |
| Multitouch | Working simultaneously |
| Landscape | Correct orientation |
| System navigation | Back/Home/Tabs preserved |
| Pause/resume | Working |
| Audio | Integrated with PipeWire |
| Haptics | Integrated and configurable |
| Bluetooth controller | Supported |
| Save/load | Working |
| Offline gameplay | Working |
| ARM64 performance | Measured |
| Existing Nuxel functions | No regressions |

The complete system must have a clear separation between:

- Native GTK4 launcher.
- SDL2 gameplay engine.
- Touchscreen HUD.
- Nuxel integration.
- Flatpak packaging.

# 12. EXECUTION STRATEGY

Work in sequential implementation phases.

Do not create competing implementations of the same components.

Where multiple specialist agents are available, they may investigate separate areas, but maintain one integration owner and one authoritative implementation.

Recommended execution order:

1. Repository reconnaissance and engine selection.
2. ARM64 engine build.
3. Minimal playable game.
4. SDL multitouch implementation.
5. Custom HUD.
6. GTK launcher.
7. Orientation and navigation.
8. Audio and haptics.
9. Flatpak and NuXtore.
10. Performance optimization.
11. Automated regression tests.
12. Documentation and completion report.

Prioritize achieving a working playable vertical slice as early as possible.

Do not spend the entire task designing beautiful menus while the game itself remains unplayable.

Do not stop after a failed build. Diagnose, repair and retry.

Do not silently disable tests to obtain a green build.

Run the existing relevant Nuxel test suites and regression gates.

Preserve all existing working functionality.

If a dependency cannot be built or a hardware API is genuinely blocked, document the evidence, implement the best supported fallback and continue with all remaining work.

# 13. DEFINITION OF DONE

I want to be able to:

1. Open NuXtore on my Samsung S10+.
2. Find DOOM.
3. Install it.
4. Open the Nuxel DOOM launcher.
5. Select Freedoom.
6. Press PLAY.
7. Have the display enter landscape.
8. Start playing immediately using only my thumbs.
9. Walk, strafe, aim, shoot and open doors simultaneously.
10. Hear the original-style game audio.
11. Feel optional haptic feedback.
12. Pause and resume.
13. Return to Nuxel Home without breaking navigation.
14. Reopen the game without losing my settings or saved progress.

No keyboard required. No mouse required. No terminal required.

**The result should feel like a dedicated Linux gaming handheld experience running on a Nuxel phone.**

Think classic DOOM meets a custom Linux handheld, with Nuxel's pixel-art identity.

Build it properly.

**THE PENGUIN HAS A SHOTGUN.** 🐧💀

---

**FINAL RESPONSE FORMAT**

When implementation finishes, provide:

- Overall completion status.
- Engine selected and version.
- Exact files added and modified.
- Flatpak application ID.
- Build commands.
- Installation commands.
- Launch command.
- Test results with pass/fail counts.
- Performance measurements.
- Hardware verification status.
- Any outstanding blockers.
- Exact commands to deploy the completed application to the connected S10+ without flashing or replacing the OS.

Do not report FULLY COMPLETE unless the acceptance criteria have genuinely been met.
