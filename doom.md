# NUXEL-A77 — OPERATION POCKET DOOM
## Build the ultimate native mobile DOOM RPG collection for Nuxel Linux

**Project codename:** Pocket DOOM
**Collection name:** Nuxel Pocket Classics
**Target devices:** Nuxel ARM64 Linux phones
**Primary hardware:** Samsung Galaxy S10+ SM-G975F, Exynos 9820
**Operating system:** Nuxel Fedora-based mobile Linux
**Primary target resolution:** Adapt to the actual device display, including the S10+'s available portrait and landscape modes
**Architecture:** Native ARM64, SDL2-based game engines, Nuxel application integration
**Distribution:** NuXtore, using the existing Nuxel application and Flatpak architecture.

## 0. THE MISSION

Build a complete mobile gaming collection containing TWO original mobile DOOM RPG experiences:

1. **DOOM RPG (2005)** — the original mobile RPG.
2. **DOOM II RPG (2009)** — the sequel.

These games were designed specifically for mobile phones with tiny screens, keypad controls and D-pad navigation.

We want to recreate that original experience as closely as possible while making the games feel completely at home on modern Nuxel Linux phones.

This is NOT a conventional DOOM FPS port.

This is NOT a Minecraft clone.

This is NOT a Java ME emulator running inside Nuxel.

We want the original mobile DOOM RPG games reconstructed and running natively through their respective reverse-engineered engines.

The ultimate experience:

- Native ARM64 game engines.
- Original game graphics and sound.
- Original gameplay.
- Original animations.
- Original menus.
- Authentic small-screen presentation.
- Virtual touchscreen D-pad.
- Dedicated action buttons.
- One-handed gameplay.
- Physical D-pad and Bluetooth controller support.
- Persistent saves.
- Offline gameplay.
- Integration into NuXtore and Nuxel Home.

The final product should feel like someone has taken the original 2005–2009 mobile DOOM gaming experience and rebuilt it specifically for a modern Linux phone.

**The original mobile gaming experience is the feature, not an inconvenience we should modernize away.**

---

# 1. MANDATORY REPOSITORY RECONNAISSANCE

Repository:

`github.com/illdynamics/nuxel`

Before implementing anything, investigate the entire existing repository and current implementation.

The ordinary DOOM application is already working in Nuxel. Preserve it.

Inspect:

- README.md
- CHANGELOG.md
- VERSION
- Existing DOOM implementation.
- Existing DOOMCRAFT work, if present.
- NuXtore.
- Application registry.
- Launcher implementation.
- Application installation and removal mechanisms.
- Flatpak manifests.
- SDL2 integration.
- Display handling.
- Phoc and compositor integration.
- Existing S10+ framebuffer presentation bridge.
- Input handling.
- Touchscreen event handling.
- Haptics.
- PipeWire integration.
- Application lifecycle.
- Application backgrounding.
- Navigation.
- Existing app-specific persistent storage conventions.
- Existing documentation.
- CI and test infrastructure.

Determine the current actual platform capabilities.

The S10+ has historically used headless Phoc with a framebuffer presentation bridge rather than a conventional `/dev/dri` configuration.

Do not assume conventional DRM/KMS access.

Do not introduce a competing display manager or compositor.

Respect the existing SDL2 and Wayland presentation infrastructure.

Inspect whether the current DOOM application already provides reusable SDL2 infrastructure, Flatpak permissions, audio services, configuration utilities and NuXtore registration.

Reuse functioning components rather than duplicating them.

Do not assume the Home application is a conventional GTK4 application. Use the real existing Nuxel UI architecture.

Do not remove or modify unrelated existing functionality.

Inspect the current Git status and preserve all user changes.

---

# 2. THE TWO GAME ENGINES

Use the existing reverse-engineered native projects as the foundation.

## GAME A — DOOM RPG (2005)

Upstream:

https://github.com/Erick194/DoomRPG-RE

Original developer:

Fountainhead Entertainment / id Software.

Reverse-engineering project:

GEC / Erick Vásquez García.

Documented upstream version: 0.2.2.

Language: C.

Documented dependencies:

- CMake.
- SDL2.
- SDL2_mixer.
- zlib.
- FluidSynth.

The upstream implementation reconstructs the original BREW version.

Its documented controls include:

| Original control | Function |
|---|---|
| Up | Move forward |
| Down | Move backward |
| Left | Turn left |
| Right | Turn right |
| A | Strafe left |
| D | Strafe right |
| Enter | Attack / talk / interact |
| Z | Next weapon |
| X | Previous weapon |
| C | Pass turn |
| Tab | Automap |
| Escape | Menu / back |

Preserve these functions.

Investigate upstream source compatibility with ARM64 and Linux.

Check existing issues, forks, pull requests and known Linux/64-bit problems.

Implement only necessary compatibility patches.

Keep those patches isolated and documented.

Do not silently alter gameplay mechanics.

### Important: 2005 asset handling

This implementation targets BREW game assets.

Investigate the actual resource loading mechanism.

The project expects its game resource archive in the format documented by upstream.

Determine how to obtain the supported resource structure from user-supplied original game data.

Investigate the `doomrpg.bar` to `DoomRPG.zip` conversion requirement.

The PortMaster implementation is a useful additional reference:

https://github.com/Cebion/DoomRPG-RE_PM

https://portmaster.games/detail.html?devices=&name=doomrpg

Its documented original-game asset requirement is a BREW `.bar` archive.

Do not assume every J2ME or BREW edition is interchangeable.

Implement explicit version detection.

Investigate whether the Java ME edition can be supported separately through an alternative native reconstruction, including:

https://github.com/sp00nznet/doomrpgrecomp

Treat alternative implementations as experimental candidates. Do not derail the primary native BREW implementation.

If the user has an unsupported original edition, explain precisely what is missing and provide an appropriate compatibility assessment.

Never report successful installation merely because an archive was accepted.

## GAME B — DOOM II RPG (2009)

Upstream:

https://github.com/Erick194/DoomIIRPG-RE

Original developer:

Fountainhead Entertainment / id Software.

Reverse-engineering project:

GEC / Erick Vásquez García.

Documented upstream version: 0.1.

Language: C.

Documented dependencies:

- CMake.
- SDL2.
- zlib.
- OpenAL.

Documented controls:

| Original control | Function |
|---|---|
| W / Up | Move forward |
| S / Down | Move backward |
| A | Strafe left |
| D | Strafe right |
| Left arrow | Turn left |
| Right arrow | Turn right |
| Enter | Attack / talk / interact |
| Z | Next weapon |
| X | Previous weapon |
| C | Pass turn |
| Tab | Automap |
| Escape | Menu |
| I | Items / information |
| O | Drinks |
| P | PDA |
| B | Deploy / return bot |

Preserve the complete control mapping.

The sequel's additional gameplay systems are important. Do not build a basic port that omits them.

Investigate:

- Inventory.
- Drinks.
- PDA.
- Companion robot.
- Robot deployment.
- Robot return.
- Original weapon systems.
- Dialogues.
- Save games.
- Level progression.
- Original sound effects.
- Original music.
- Animations.
- Original menus.

### Important: DOOM II RPG assets

Investigate the actual upstream resource-loading mechanism.

The iOS IPA data route is documented by the existing Doom II RPG Vita implementation:

https://github.com/Rinnegatamante/DoomIIRPG-RE

Inspect the Vita adaptation and its data loading approach, but do not blindly reuse platform-specific Vita code.

Investigate whether the upstream implementation expects the iOS `.ipa` data layout, a specific filename or a particular extracted directory structure.

The importer must be built around verified source-code requirements.

Do not assume that the 2005 BREW `.bar` format works for the sequel.

Do not create a universal importer that silently mixes incompatible game versions.

Investigate current Linux compilation compatibility and existing open pull requests.

The documented 0.1 implementation should be treated as a starting point, not proof that the current main branch builds successfully on Fedora ARM64.

Repair genuine build problems and verify actual game execution.

---

# 3. IMPLEMENT A SHARED NUXEL POCKET DOOM COLLECTION

The two games should appear together in one beautifully designed Nuxel mobile gaming experience.

Suggested application identity:

`org.nuxel.PocketDoom`

However, inspect the existing Nuxel application naming and packaging conventions before adopting this exact ID.

Preferred navigation:

**NUXEL HOME → NUXEL DOOM → POCKET CLASSICS**

Show two separate game entries:

<pre>
+-----------------------------------+
|          NUXEL POCKET DOOM        |
|                                   |
|    [ DOOM RPG - 2005 ]            |
|                                   |
|    [ DOOM II RPG - 2009 ]         |
|                                   |
|    Settings                       |
|    Game Data Manager              |
|    Controls                       |
+-----------------------------------+
</pre>

Each game must have:

- Individual executable.
- Individual configuration.
- Individual save directory.
- Individual resource directory.
- Individual import validation.
- Independent launch and shutdown lifecycle.

Avoid building one heavily modified game engine containing both games' logic.

Keep the engines separated.

Build a shared Nuxel integration layer for:

- Launcher.
- Settings.
- Touch controls.
- Gamepad input.
- Audio routing.
- Haptics.
- Save location management.
- Installation state.
- Error reporting.

The two games must continue to work independently.

If one crashes, it must not corrupt the other game's settings or save data.

The launcher should tell the user which game data is installed and which is missing.

---

# 4. THE MOST IMPORTANT FEATURE: AUTHENTIC MOBILE D-PAD CONTROLS

We want to recreate the actual feel of playing these games on old Nokia, Sony Ericsson and other feature phones.

This is not a modern FPS joystick.

The D-pad is the primary interaction method.

The controls must respect the original discrete, turn-based mechanics.

Do not convert movement into continuous free-running joystick movement.

## A. Virtual touchscreen D-pad

Implement a large, comfortable virtual D-pad.

The D-pad should support:

- Up.
- Down.
- Left.
- Right.
- Accurate individual button events.
- Configurable touch repeat.
- Adjustable size.
- Adjustable opacity.
- Haptic confirmation.
- Immediate button release.
- Multitouch support.

Map the controls according to each game's native key mapping.

For example, in DOOM RPG:

- Up = move forward.
- Down = move backward.
- Left = turn left.
- Right = turn right.
- Strafe left/right = secondary controls.

For DOOM II RPG:

- Up/down = forward/backward.
- Left/right = rotation.
- Strafe left/right = additional controls.

Preserve the games' original turn-based movement semantics.

Repeated movement should be deliberate and configurable.

Never generate uncontrolled repeated turns while a button is held.

Support optional directional repeat with a configurable delay.

## B. Action buttons

Implement touchscreen equivalents of the original phone action buttons.

Primary actions:

- ATTACK / TALK / INTERACT.
- SKIP TURN.
- AUTOMAP.
- MENU / BACK.
- NEXT WEAPON.
- PREVIOUS WEAPON.

DOOM II RPG must also support:

- ITEMS / INFORMATION.
- DRINKS.
- PDA.
- ROBOT DEPLOY / RETURN.

Do not hide sequel-specific functions.

Use a secondary actions drawer or compact expansion menu if necessary.

Every original function must remain accessible.

## C. Two-handed and one-handed modes

Support:

1. Two-thumb landscape mode.
2. Two-thumb portrait mode.
3. Left-handed mode.
4. Right-handed mode.
5. Compact one-handed mode.

The compact one-handed layout should prioritize:

- D-pad.
- Action.
- Back.
- Menu.

Provide configurable button positioning.

Do not make buttons overlap or interfere with the game's actual rendered controls.

## D. Physical controller support

Support:

- Bluetooth gamepads.
- SDL-compatible controllers.
- Physical D-pads.
- ABXY buttons.
- Shoulder buttons.
- Select and Start.

Suggested default controller mapping:

| Controller | Action |
|---|---|
| D-pad up/down | Forward/backward |
| D-pad left/right | Turn |
| A | Action / attack / interact |
| B | Pass turn / back |
| X | Previous weapon |
| Y | Automap |
| L1 | Strafe left |
| R1 | Strafe right |
| L2 | Previous weapon |
| R2 | Next weapon |
| Start | Menu |
| Select | Secondary menu |

Make the mapping configurable.

Preserve native engine input compatibility.

Do not use global OS keyboard injection.

Do not create a privileged uinput daemon.

Translate touchscreen controls into engine-local SDL events or directly into the existing engine input mapping.

---

# 5. RECREATE THE ORIGINAL SMALL-SCREEN EXPERIENCE

This is where we distinguish Pocket DOOM from the existing normal DOOM implementation.

Do not force either game into the full-screen modern FPS interface.

Preserve the original mobile game's visual structure.

The original games were designed around compact display resolutions and keypad navigation.

Build a responsive rendering layout that keeps the authentic visual proportions.

### Requirements

- Preserve the original game's viewport aspect ratio.
- Preserve original asset proportions.
- Use crisp nearest-neighbour scaling.
- Avoid blurry texture interpolation.
- Preserve original HUD placement.
- Preserve original portrait/menu layouts where supported.
- Respect the actual game interface.
- Never stretch the original images to fill an arbitrary screen.

Support both portrait and landscape if the underlying engine permits it reliably.

Default to portrait-oriented mobile presentation when that matches the original game's supported UI.

Do not unnecessarily rotate the entire phone.

Keep Nuxel's three navigation controls working.

### Optional display modes

Implement:

**ORIGINAL PHONE MODE**

Faithful original screen layout with accurate scaling and original visual proportions.

**MODERN MOBILE MODE**

The original game viewport is combined with carefully positioned modern touchscreen controls.

**PIXEL PERFECT MODE**

Nearest-neighbour scaling and integer scaling where practical.

**COMPACT MODE**

Prioritize the original small-screen experience and one-handed operation.

Allow users to switch modes without losing game progress.

---

# 6. ORIGINAL GRAPHICS AND SOUND

The original visual and audio identity is critical.

Do not replace original game graphics with generic DOOM assets.

Do not substitute Freedoom assets.

Do not reuse assets from the normal Doom FPS application unless they are genuinely part of these specific games.

Use the actual locally supplied original game data.

Preserve:

- Original weapon sprites.
- Original monster sprites.
- Original environments.
- Original menu graphics.
- Original portraits.
- Original inventory graphics.
- Original animations.
- Original UI graphics.
- Original sound effects.
- Original music.
- Original dialogue-related assets.

Maintain the original colour palettes.

Do not apply the DOOMCRAFT graphics transformations automatically.

These are two separate products.

### Optional experimental graphics

Provide the possibility of a separate optional visual enhancement in the future, but prioritize faithful original presentation first.

---

# 7. NUXEL MOBILE UI DESIGN

Create a dedicated Pocket DOOM visual identity.

Design direction:

- Retro mobile phone gaming.
- Early-2000s handheld gaming.
- Dark metallic UI.
- Chunky pixel typography.
- Classic arcade elements.
- Minimal glow.
- Crisp icons.
- Nuxel branding.

Create original application artwork for:

- Pocket DOOM collection.
- DOOM RPG 2005.
- DOOM II RPG 2009.
- Game data import.
- Controller.
- Virtual D-pad.
- Automap.
- Inventory.
- PDA.
- Robot.
- Game settings.

Do not copy proprietary cover artwork or promotional imagery.

Create original launcher artwork inspired by early mobile gaming.

Use the existing Nuxel design system and asset conventions.

## Home screen

Show:

- Two game tiles.
- Individual installed/missing data indicators.
- Last played game.
- Last played date.
- Continue button when a valid save exists.
- New Game.
- Settings.
- Import Game Data.
- Controller Configuration.
- About and credits.

## Game-specific menus

Keep each game's menu structure authentic.

Do not force the same menu into both engines.

DOOM II RPG should have its own controls and menu configuration to accommodate its additional gameplay systems.

---

# 8. GAME DATA IMPORTER AND VALIDATION SYSTEM

Build a safe, native Nuxel game-data import experience.

The user must be able to import their own legally obtained original game data.

Do not distribute commercial game data.

Do not download copyrighted game assets automatically.

Do not include commercial game archives, extracted sprites, music, sounds or compiled original game binaries in Git, Flatpak or NuXtore.

Use only original data the user is entitled to provide.

## A. DOOM RPG importer

Support the verified BREW resource format required by the selected engine.

Investigate:

- `.bar`
- Converted `.zip` data.
- Original resource structure.
- Expected filenames.
- Required resources.
- Archive validation.
- Soundfont requirement.
- Data compatibility.

Implement a guided import interface.

Display:

- Detected game version.
- Detected archive format.
- Required conversion status.
- Resource verification result.
- Missing files.
- Installation status.

If a converter is needed:

- Prefer an audited open-source implementation.
- Pin its source.
- Verify its license.
- Build it natively for ARM64.
- Do not download mysterious precompiled converters.
- Keep the original archive unchanged.

The importer must not silently modify the user's original file.

## B. DOOM II RPG importer

Support the verified resource format required by the selected implementation.

Investigate the iOS `.ipa` route and actual expected folder hierarchy.

Implement:

- IPA validation.
- Safe archive extraction.
- Required directory detection.
- Missing-resource detection.
- Asset compatibility verification.
- Installation into private application storage.

Never assume that extracting an IPA's outer directory is sufficient.

Inspect the real expected `Payload/*.app` resource structure and implement the required extraction correctly.

## C. Secure archive handling

Treat every imported file as untrusted input.

Protect against:

- Path traversal.
- Symlink traversal.
- Malicious archive entry names.
- Oversized extracted files.
- Archive bombs.
- Duplicate conflicting files.
- Unexpected filesystem writes.
- Invalid nested archives.

Use safe temporary directories.

Verify expected file checksums and structures where known.

Never run executable code from an imported archive.

## D. Data persistence

Use separate game-data storage.

For example:

```text
~/.var/app/<verified-application-id>/
    data/
        doom-rpg/
            resources/
            saves/
            config/
        doom-ii-rpg/
            resources/
            saves/
            config/
```

Adapt this to the actual Flatpak and XDG storage conventions.

Keep imported original game files persistent when updating the application.

Uninstalling the engines must not accidentally erase user-imported game data without an explicit user decision.

---

# 9. SAVE GAMES AND GAME CONTINUITY

Both games must preserve their original save systems.

Verify:

- Save creation.
- Save loading.
- Multiple save slots.
- Save deletion.
- Game state restoration.
- Inventory persistence.
- Weapon persistence.
- Mission progression.
- Game-specific state.

If the engines currently use relative save paths or hardcoded locations, patch them to use Nuxel's private persistent application storage.

Do not overwrite existing saves during upgrades.

Add optional automatic backup before application updates.

Do not invent a replacement save format when the original implementation can be preserved.

If a save conversion is necessary, make it explicit, reversible and tested.

---

# 10. AUDIO, HAPTICS AND SYSTEM INTEGRATION

## Audio

The 2005 implementation uses SDL2_mixer and FluidSynth according to upstream documentation.

The 2009 implementation documents OpenAL.

Investigate the actual audio implementation and use the existing Nuxel audio infrastructure where possible.

Requirements:

- Original music.
- Original sound effects.
- Correct volume levels.
- Audio focus.
- Suspend/resume.
- No competing audio daemons.
- No interference with Nuxel system sounds.

For DOOM RPG, provide the required soundfont configuration if the game uses FluidSynth.

Do not bundle copyrighted soundfonts without permission.

## Haptics

Use Nuxel's existing haptics service.

Optional haptic feedback for:

- D-pad taps.
- Menu selection.
- Attack.
- Interaction.
- Damage.
- Important notifications.

Provide configurable strength and disable functionality.

Do not create continuous vibrations from touch-repeat loops.

## System navigation

Preserve Back / Home / Tabs.

Requirements:

BACK:
Return to the active game menu or exit an appropriate submenu.

HOME:
Immediately return to Nuxel Home through the established system navigation mechanism.

TABS:
Open the existing application switcher.

Never disable the system HOME mechanism.

Never leave the game in an invalid foreground or suspended state.

Audio and haptics must stop or pause appropriately when leaving the application.

---

# 11. PERFORMANCE AND ARM64 COMPATIBILITY

Optimize specifically for the Exynos 9820.

These are lightweight mobile RPG engines, so we should not need excessive CPU or GPU resources.

Prioritize:

- Native ARM64 compilation.
- Efficient SDL2 rendering.
- Low memory consumption.
- Crisp original-resolution rendering.
- Efficient texture caching.
- Predictable frame pacing.
- Fast startup.
- Low power consumption.
- Proper audio resource management.

Do not add unnecessary high-performance graphics dependencies.

Do not assume `/dev/dri` exists.

Respect the actual Nuxel rendering path.

Aim for responsive rendering at 30–60 FPS, subject to the original games' actual frame behavior.

More importantly, preserve input responsiveness and animation timing.

Do not force modern animation speeds where doing so changes the original gameplay.

Provide a performance diagnostics option.

Report actual memory consumption and frame timings.

---

# 12. FLATPAK AND NUXEL INTEGRATION

Package the collection using the actual current Nuxel application distribution model.

Inspect existing Flatpak manifests before creating new ones.

Use native ARM64 builds.

Keep engine dependencies isolated where appropriate.

Provide:

- Application metadata.
- Desktop entries.
- Application icons.
- ARM64 binaries.
- Correct runtime dependencies.
- Resource directories.
- Game-specific configuration.
- Persistent storage.
- Game-data import access.
- License files.
- Source references.

Minimize permissions.

Expected capabilities should be limited to actual requirements:

- Existing Wayland display mechanism.
- Audio output.
- Controller access where required.
- XDG document portal.
- Required session services.

No broad filesystem permissions.

No unnecessary network access.

No unrestricted device access.

No root privileges.

## Source licensing

Both reverse-engineered projects advertise GPL-3.0.

Inspect the precise licenses of all source components and dependencies.

Preserve original copyright notices.

Include complete applicable license texts.

Ensure corresponding-source and build-script obligations are met for distributed GPL components.

Maintain clean provenance for all Nuxel patches.

Prefer retaining the two upstream engines as independent executable projects.

Do not copy upstream code into unrelated proprietary Nuxel components.

Do not claim that using separate processes automatically resolves every licensing obligation.

---

# 13. AUTOMATED TESTING

Create proper automated tests.

## A. Build tests

- Native x86_64 build.
- Native aarch64 build.
- Fedora dependency resolution.
- SDL2 initialization.
- Audio initialization.
- Engine startup.
- Resource discovery.
- Application termination.

## B. DOOM RPG tests

- Import supported BREW archive.
- Validate converted resources.
- Load menu.
- Start new game.
- Load save.
- Move forward.
- Move backward.
- Turn left.
- Turn right.
- Strafe.
- Attack.
- Talk.
- Interact.
- Pass turn.
- Open map.
- Change weapons.
- Save and restore progress.

## C. DOOM II RPG tests

- Import supported iOS resource package.
- Extract correct resources.
- Load menu.
- Start new game.
- Load save.
- Movement.
- Turning.
- Strafing.
- Attacking.
- Items.
- Drinks.
- PDA.
- Bot deployment.
- Bot return.
- Automap.
- Weapon selection.
- Save and restore progress.

## D. Touchscreen tests

- Individual directional presses.
- Rapid D-pad tapping.
- Controlled button repeat.
- Simultaneous multitouch.
- Action buttons.
- Secondary menu.
- Left-handed mode.
- Right-handed mode.
- One-handed mode.
- Finger cancellation.
- Application focus loss.
- Pause/resume.

Verify that a lost touch event never leaves an input button stuck.

## E. Regression tests

- Existing normal DOOM FPS still launches.
- Existing DOOMCRAFT work remains intact.
- Existing NuXtore remains functional.
- Nuxel Home continues working.
- Back/Home/Tabs continue working.
- Other applications continue working.
- Audio routing restores correctly.
- Haptics remain available.
- Existing system navigation is not broken.

## F. Physical device verification

Use the S10+ where available.

Test actual game execution, not just engine startup.

Record:

- Startup time.
- Average memory consumption.
- CPU utilization.
- Rendering frame rate.
- Touch input latency.
- Audio functionality.
- Save persistence.

Clearly separate automated test results from physical hardware verification.

Do not claim real device testing without actually performing it.

---

# 14. IMPLEMENTATION ORDER

Work in manageable stages, but continue until the implementation is complete.

### Phase 1 — Reconnaissance

Inspect Nuxel and both upstream repositories.

Establish the precise dependency, resource and build requirements.

Identify existing Linux/ARM64 compatibility problems.

Produce a brief technical assessment.

### Phase 2 — DOOM RPG 2005

Build the native ARM64 version.

Resolve dependencies.

Implement asset importing.

Get the actual game menu running.

Get a complete playable campaign working with user-supplied data.

### Phase 3 — DOOM II RPG 2009

Build the native ARM64 version.

Resolve upstream compatibility issues.

Implement IPA data importing.

Get the game menu running.

Verify its additional gameplay functions.

### Phase 4 — Shared Nuxel controls

Implement the touch D-pad system.

Map every game function correctly.

Add controller support.

Implement portrait and landscape interfaces.

### Phase 5 — Pocket DOOM launcher

Implement the combined application experience.

Add two separate game entries.

Add settings and data import management.

### Phase 6 — Audio and haptics

Integrate both engines with Nuxel system services.

Test actual audio output.

### Phase 7 — Packaging

Integrate NuXtore.

Create reproducible ARM64 Flatpak builds.

Test installation and uninstall behavior.

### Phase 8 — Optimization

Tune the engines for Exynos 9820.

Test responsiveness and battery consumption.

### Phase 9 — QA and documentation

Run automated and actual hardware tests.

Fix regressions.

Complete documentation.

Create deployment instructions.

---

# 15. DOCUMENTATION TO ADD

Create:

```text
docs/games/pocket-doom.md
docs/games/pocket-doom-doom-rpg.md
docs/games/pocket-doom-doom-ii-rpg.md
docs/games/pocket-doom-controls.md
docs/games/pocket-doom-game-data.md
docs/games/pocket-doom-troubleshooting.md
docs/games/pocket-doom-build.md
```

Document:

- Game selection.
- Engine versions.
- Source repositories.
- License details.
- Build commands.
- Resource requirements.
- Game-data importing.
- Touch controls.
- Physical controllers.
- Save locations.
- Audio configuration.
- Known limitations.
- Troubleshooting.
- Actual S10+ performance.

Update README.md and CHANGELOG.md where appropriate.

Do not arbitrarily bump the Nuxel operating system version for this individual feature.

---

# 16. ACCEPTANCE CRITERIA

| Feature | Required result |
|---|---|
| DOOM RPG 2005 | Native ARM64 executable |
| DOOM II RPG 2009 | Native ARM64 executable |
| Independent engines | Yes |
| Independent saves | Yes |
| Original game assets | Preserved |
| Game-data importer | Working |
| Original mobile presentation | Preserved |
| Virtual D-pad | Working |
| Touch action buttons | Working |
| One-handed mode | Working |
| Left-handed mode | Working |
| Physical controller | Working |
| Portrait display | Supported where engine permits |
| Landscape display | Supported where engine permits |
| Audio | Working |
| Haptics | Optional and working |
| NuXtore | Integrated |
| Flatpak | Working |
| Offline operation | Working |
| Normal DOOM FPS | Unaffected |
| Nuxel navigation | Unaffected |
| S10+ performance | Measured |

A title must not be marked playable if it only opens a blank window or displays a title screen without actually supporting gameplay.

---

# 17. DEFINITION OF DONE

I want to use my S10+ like an old-school mobile gaming phone.

I open Nuxel Home.

I launch Nuxel Pocket DOOM.

I see two games:

**DOOM RPG (2005)**

**DOOM II RPG (2009)**

I select either game and immediately get that authentic old-school mobile interface.

I can:

- Move using the virtual D-pad.
- Turn using directional buttons.
- Strafe using secondary controls.
- Shoot and interact.
- Skip turns.
- Open inventory and menus.
- Use the sequel's PDA.
- Deploy and control the sequel's robot.
- View the automap.
- Save and continue.
- Play entirely offline.
- Use physical controller buttons if connected.

Everything feels natural on a modern Linux phone without sacrificing the original gameplay experience.

No external keyboard.

No mouse.

No Android emulator.

No Java ME runtime.

No desktop UI pretending to be a mobile game.

**Native Linux. Native ARM64. Original DOOM mobile RPG gameplay.**

---

# 18. AUTONOMOUS EXECUTION RULES

This is an implementation task, not a research-only assignment.

Do not stop after inspecting the repositories.

Do not stop after creating build scripts.

Do not stop after one game works.

Work through both implementations and complete every achievable integration task.

When one upstream engine has a blocker:

1. Identify the exact failure.
2. Inspect related upstream fixes and forks.
3. Determine whether a small compatibility patch is appropriate.
4. Implement and test the patch.
5. Continue with the remaining integration work.

Do not invent missing game assets.

Do not download commercial game data.

Do not claim an untested engine works.

Do not compromise the working Nuxel DOOM FPS application.

Do not delete or overwrite user changes.

Do not disable existing regression tests.

Keep upstream patches reproducible.

When useful, delegate independent reconnaissance or testing tasks to specialist agents, but maintain one integration owner and one authoritative implementation.

Prioritize real gameplay over decorative UI work.

A complete working first title is better than two beautiful but nonfunctional launchers. Nevertheless, the final deliverable must make a genuine attempt at both engines.

If one game cannot be completed due to a verified upstream limitation, provide the working first game and the most complete safe implementation of the second, with the exact remaining blocker documented.

# 19. FINAL DELIVERY REPORT

When implementation finishes, provide:

1. Overall status.
2. DOOM RPG engine version and source commit.
3. DOOM II RPG engine version and source commit.
4. Exact ARM64 build results.
5. Exact files added and modified.
6. Flatpak IDs.
7. NuXtore integration details.
8. Game-data formats supported.
9. Touchscreen control mappings.
10. Physical controller mappings.
11. Save-data locations.
12. Test results and pass/fail counts.
13. Actual S10+ verification.
14. Memory and performance measurements.
15. Known limitations.
16. Installation commands.
17. Update commands.
18. SSH deployment commands for the connected S10+.

Do not flash or replace the Nuxel operating system.

Do not reboot or erase the phone automatically.

The application should be deployable independently.

**FINAL PROJECT VISION:**

NUXEL POCKET DOOM.

Two legendary mobile RPGs.

One native Linux phone.

A proper virtual D-pad.

The original mobile gaming experience brought back to life.

**THE PENGUIN HAS FOUND ITS OLD NOKIA COLLECTION.** 🐧📱💀
