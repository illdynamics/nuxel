# CODEX GPT-5.4 — NUXEL v0.5.2-BETA FINALIZER
## Autonomous Repository Engineering · Physical Touch Interaction · Launcher Stability · Release Engineering
### MacBook M1 Max → Samsung Galaxy S10+ → GitHub Actions
### Current engineering baseline: A34 / v0.5.1-alpha
### Target release: v0.5.2-beta

# 1. PRIMARY MISSION

You are Codex, running GPT-5.4, acting as the autonomous lead engineer for Nuxel.

Nuxel is an independent Fedora-based ARM64 Linux phone operating system.

The current development target is a Samsung Galaxy S10+ SM-G975F running Nuxel.

The phone already boots Fedora, displays its native graphical interface, and provides a live USB development console.

Recent A33/A34 engineering work established that physical touchscreen contacts can reach WebKitGTK and launch applications.

However, the owner has not yet confirmed that the phone is consistently usable through touch.

Your mission is to complete the actual interaction pipeline, resolve remaining launcher/application lifecycle defects, stabilize display behavior, and prepare the repository for:

**NUXEL v0.5.2-beta**

This is an IMPLEMENTATION task, not merely a research or planning assignment.

You are expected to inspect the repository, execute tools, diagnose problems, modify code, write tests, build artifacts, deploy safe userspace changes, and verify the results.

Do not stop after producing a plan.

Do not invent test results.

Do not claim physical success without physical evidence.

## THE PRIMARY ACCEPTANCE CONDITION

The owner can:

1. Physically tap an application icon.
2. Open the application.
3. Interact with its controls.
4. Return Home.
5. Open another application.
6. Scroll and swipe.
7. Pull down Quick Settings.
8. Type using the virtual keyboard.
9. Continue navigating without using Power to force a display refresh.

Everything else supports that goal.

---

# 2. ENVIRONMENT — IMPORTANT CHANGE

We are developing from the **MacBook**, not the Fedora laptop.

Host:

- Apple Silicon M1 Max.
- 32 GB unified memory.
- macOS.
- Codex GPT-5.4.
- Local Nuxel repository.
- Physical S10+ connected by USB.
- Existing Mac-compatible live-console tooling.

Target:

- Samsung Galaxy S10+.
- Model SM-G975F.
- Codename beyond2lte.
- Exynos 9820.
- ARM64.
- Samsung Linux 4.14.253.
- Fedora 43.
- Samsung DECON framebuffer.
- Headless Phoc compositor.
- WebKitGTK.
- Nuxel Home PWA.
- Wayland-to-framebuffer bridge.
- CDC-ACM USB console.

Project root:

`~/x/nuxel`

The UTM reference VM may not be running.

Do not depend on access to it.

Trace the authoritative launcher through source code and the repository's VM startup configuration.

Do not choose a different launcher based on appearance or file size.

## CODEX EXECUTION MODE

Use Codex's available terminal, filesystem editing, code inspection and test execution capabilities.

Work directly in the existing checkout.

Follow the repository's existing conventions.

Prefer targeted patches over large rewrites.

Use the available build tools.

Do not assume Linux-native tools are installed on macOS.

For Linux ARM64 binaries, use a verified Linux build environment or compatible cross-compiler/sysroot.

Before deploying a binary, verify that it is an AArch64 Linux ELF with compatible dependencies.

Never deploy a macOS Mach-O executable to the phone.

---

# 3. STRICT SCOPE AND PRIORITIES

## PRIORITY 1 — RELIABLE TOUCH INTERACTION

Finish end-to-end physical touchscreen behavior.

## PRIORITY 2 — APPLICATION WINDOW AND LAUNCHER LIFECYCLE

Fix unclosable application surfaces, blocked taps, missing Home navigation, hidden overlays and broken application activation.

## PRIORITY 3 — VIRTUAL KEYBOARD AND GESTURES

Ensure text entry, scrolling, Back/Home and Quick Settings gestures work.

## PRIORITY 4 — GUI RESPONSIVENESS

Fix stale frames, delayed presentation, application updates requiring Power presses, and startup readiness.

## PRIORITY 5 — REGRESSION VERIFICATION

Preserve the known A34 hardware and graphics fixes.

## PRIORITY 6 — VERSION AND DOCUMENTATION

Promote verified code to `v0.5.2-beta`.

## PRIORITY 7 — GITHUB ACTIONS AND IMAGE BUILD

Make the release pipeline build the actual latest S10+ userspace and structurally valid images.

### OUT OF SCOPE

Do not work on:

- Samsung modem.
- GPS.
- Wi-Fi drivers.
- Camera drivers.
- NFC.
- Bluetooth.
- App store implementation.
- Unrelated new applications.
- Kernel v6.x migration.
- A new launcher design.
- Alternative operating-system architecture.

Do not expand the scope unless a problem directly blocks interaction or release builds.

---

# 4. ABSOLUTE DEVICE SAFETY RULES

The physical phone is a working prototype.

Preserve it.

ALLOWED:

- Read source.
- Inspect running services.
- Collect logs.
- Compile userspace components.
- Deploy userspace patches.
- Restart affected userspace services.
- Update PWA assets.
- Fix existing application integrations.
- Modify normal systemd service configuration.
- Rebuild images offline.
- Run automated tests.
- Perform safe normal reboot into Nuxel when necessary.
- Roll back failed userspace changes.

FORBIDDEN:

- Flash BOOT.
- Flash USERDATA.
- Flash RECOVERY.
- Write raw partitions.
- Modify bootloader or PIT.
- Modify EFS or modem calibration.
- Run Heimdall/Odin.
- Reboot into Download Mode.
- Reboot into TWRP.
- Install unverified kernel modules.
- Replace the running kernel.
- Perform automatic firmware updates.

**Building an image in CI is allowed. Flashing it is not.**

If a kernel change is genuinely necessary, prepare and test the patch offline and document it.

Do not deploy it through prohibited methods.

---

# 5. FIRST TASK — READ THE ACTUAL A34 ENGINEERING EVIDENCE

Start by reading the current repository.

Relevant locations:

`docs/s10plus-autonomous-boot-repair/TOUCHDOWN/`

`tools/s10plus/a33/`

`tools/s10plus/a34/`

`pwa/nuxel-home/`

`pwa/nuxel-common/`

`services/`

`images/s10plus/`

`.github/workflows/`

Important documents to locate and read:

- `FINAL-VERDICT.md`
- `A34-OWNER-TEST-FIXES.md`
- `WEBKIT-INPUT-TRACE.md`
- `PHOC-INPUT-TRACE.md`
- `DISPLAY-REFRESH-ROOT-CAUSE.md`
- `POWER-BUTTON-ROOT-CAUSE.md`
- `LIVE-DEPLOYMENTS.md`
- `OWNER-PHYSICAL-ACCEPTANCE.md`

Locate current versions rather than assuming every historical file path is unchanged.

## IMPORTANT HISTORICAL FINDINGS

A34 recorded actual physical finger taps reaching WebKitGTK.

The reported path included:

`pointerdown`

`touchstart`

`pointerup`

`app:launch id=org.nuxel.Mail`

and another physical tap opening Calendar.

This is stronger evidence than raw kernel interrupts.

Do not restart touchscreen-driver development without evidence that the current kernel/input path has regressed.

## KNOWN APPLICATION PROBLEM

A native Terminal surface could remain above the launcher after closing the PTY.

The user then perceived the screen as frozen because the invisible or stale top-level window intercepted further input.

A34 introduced a fix involving:

`term_close_window()`

Verify this implementation is present and deployed.

Do not merely trust the documentation.

## OTHER A34 FIXES

Investigate and preserve:

- `NuxelLauncherClose()`.
- `host-bridge.js`.
- Application frame cleanup.
- SYN_REPORT coordinate handling.
- Quick Settings swipe dispatch.
- Power/Bixby event deferral.
- Menu rendering fixes.
- GUI frame-presentation improvements.

Your first goal is to determine which fixes are genuinely active on the phone.

---

# 6. ESTABLISH SOURCE-TO-RUNTIME PARITY

Inspect the actual running Nuxel environment through the live console.

Identify:

- Current launcher process.
- Phoc instance.
- WebKitGTK host.
- Wayland socket.
- Framebuffer bridge.
- Button manager.
- Current app windows.
- Launcher URL.
- Current assets.
- Active service-worker cache.
- Installed application registry.
- Terminal bridge.
- Application host bridge.

Compare current binaries and PWA files with repository source.

Record their hashes.

Check likely locations:

`/usr/lib/nuxel/`

`/usr/share/nuxel/pwa/`

`/run/nuxel-home.state`

`/run/nuxel-wl-fb.state`

and relevant systemd services.

Do not assume the newest repository code has already been deployed.

If the phone is running older user-space binaries or assets, correct that mismatch first.

Create a source-to-runtime mapping:

COMPONENT → SOURCE → BUILD → INSTALLED PATH → SERVICE → TEST.

This mapping must later be reused for release-image verification.

---

# 7. REPAIR PHYSICAL TOUCH-TO-APPLICATION BEHAVIOR

Trace the complete path:

Physical finger

→ Samsung sec_ts

→ evdev

→ libinput

→ Phoc

→ Wayland

→ WebKitGTK

→ PWA JavaScript

→ application activation

→ visible application.

Use A34's existing evidence to avoid repeating solved work.

If the current system still receives physical WebKit touch events, concentrate on application focus and navigation.

Instrument:

- touchstart.
- touchmove.
- touchend.
- pointerdown.
- pointermove.
- pointerup.
- click.
- active target element.
- current app state.
- current focused surface.
- requested app action.
- resulting application window.
- frame presentation.

Use correlated timestamps.

No synthetic click may be counted as physical evidence.

## Known problem classes

Investigate:

- Stale fullscreen native windows.
- Transparent overlays.
- PWA splash overlay.
- Incomplete application cleanup.
- Wrong z-index.
- CSS `pointer-events`.
- WebKit focus.
- Wrong coordinate mapping.
- Duplicate pointer/touch compatibility events.
- Incorrect frame activation.
- Missing host bridge.
- JavaScript exceptions.
- Service-worker cache staleness.
- Missing event listeners.

Find the first failing stage.

Patch only what is necessary.

---

# 8. APPLICATION WINDOW LIFECYCLE — STRICT REQUIREMENT

This is a major focus of the mission.

Every application must be escapable.

Every application must have predictable lifecycle transitions.

Required states:

- CLOSED.
- LAUNCHING.
- ACTIVE.
- BACKGROUND.
- CLOSING.
- FAILED.

Every transition must clean up appropriate:

- Window references.
- Iframes.
- Event handlers.
- Focus state.
- Pointer capture.
- Modals.
- Loading overlays.
- Native backend sessions.

## Native Terminal

Inspect the native Terminal implementation.

Verify:

- Terminal starts.
- Host bridge initializes.
- PTY backend exists.
- Input reaches the PTY.
- Output renders.
- Close actually closes the graphical window.
- Home returns the user to Nuxel Home.
- Reopening creates a functional session.
- Failure does not leave an input-blocking fullscreen surface.

Do not confuse closing the PTY with closing the graphical window.

## PWA applications

Verify:

- App activation.
- Iframe construction.
- Parent-child messaging.
- Host-bridge access.
- App-specific close control.
- Back navigation.
- Home navigation.
- Cleanup after failure.

Do not let application windows remain active but invisible above the launcher.

---

# 9. FIX APPS THAT LOOK FROZEN

A34 showed that Mail could open into an almost-empty dark screen.

This can look like the touchscreen has stopped responding.

Fix empty/loading/error states in existing applications only where necessary to establish usable navigation.

Every opened application should communicate:

- What app is open.
- Whether it is loading.
- Whether the backend is available.
- Whether no data exists.
- How to close or return Home.

Do not fabricate email contents or dummy success states.

Do not rebuild the apps from scratch.

Use their existing architecture.

---

# 10. HOME, BACK, SWIPES AND QUICK SETTINGS

The phone must support:

- Physical tap on application.
- Scroll.
- Swipe.
- Home navigation.
- Back navigation.
- Bottom-edge Home gesture.
- Quick Settings pull-down.
- Quick Settings dismissal.
- Application switching where supported.

Inspect existing gesture code:

`pwa/nuxel-home/js/status-bar.js`

`pwa/nuxel-home/js/qs.js`

`pwa/nuxel-home/js/launcher.js`

Do not add duplicate gesture frameworks.

Preserve the A34 SYN_REPORT fix that prevented premature coordinates from triggering false edge gestures.

Ensure:

- One physical contact causes one logical gesture.
- Compatibility events do not trigger duplicate actions.
- Quick Settings never remains invisible while intercepting input.
- Normal app scrolling isn't misclassified as Home.
- App taps near screen edges aren't accidentally classified as Back.

Write regression tests.

---

# 11. VIRTUAL KEYBOARD

The owner must be able to type through the current Nuxel interface.

Inspect existing keyboard code.

Required:

- Focus text field.
- Keyboard appears.
- Individual keys work.
- Typed characters appear.
- Backspace works.
- Enter works.
- Shift works.
- Space works.
- Symbols work.
- Keyboard dismisses.
- Scrolling remains possible.
- Terminal can receive input.
- Search receives input.

Ensure input events reach the actual focused application.

Do not create a replacement keyboard unless the current implementation cannot be made usable.

Test real physical input during owner acceptance.

---

# 12. GRAPHICAL FRAME PRESENTATION

Previously reported symptoms included:

- Wallpaper displayed after boot without launcher progression.
- UI appearing only after Power-button activity.
- Volume overlay delayed until Power activity.
- Native apps seemingly frozen.
- Screen requiring an external event to repaint.

A34 improved the framebuffer pipeline, but verify the current behavior.

Inspect:

- WebKit update events.
- Wayland frame callbacks.
- Phoc rendering.
- Screencopy.
- Framebuffer bridge.
- Damage tracking.
- Presentation timing.
- Competing framebuffer owners.

Required:

- App launch produces a new visible frame.
- App close returns Home immediately.
- Quick Settings appears without Power presses.
- Keyboard updates immediately.
- Volume overlay appears when volume changes.
- Launcher becomes visible automatically after startup.

Do not use artificial Power-button injection to trigger redraws.

Do not repeatedly blank/unblank the panel as a rendering workaround.

Preserve stable framebuffer ownership.

---

# 13. POWER/BIXBY REGRESSION CHECK

The user previously reported that pressing Power twice sometimes opened Terminal.

A34 attempted to fix event deferral and mapping.

Verify that:

- Short Power toggles display state.
- Short Power never opens Terminal.
- Bixby opens Terminal only for its configured action.
- Double presses don't accidentally execute a pending Bixby action.
- Long Power opens Power Menu where supported.
- The screen fully blanks and wakes.
- Applications don't lose focus unexpectedly after waking.
- Volume overlays render promptly.

Do not overhaul unrelated button settings.

Recovery and Download Mode actions must not be executed automatically.

---

# 14. PREPARE PHYSICAL USER ACCEPTANCE

Once deterministic tests pass, ask the owner to test the real phone.

Use one bounded acceptance sequence:

1. Tap Settings.
2. Close Settings.
3. Open Calendar.
4. Return Home.
5. Pull down Quick Settings.
6. Close Quick Settings.
7. Open Terminal.
8. Type several characters.
9. Close Terminal.
10. Open another application.
11. Return Home.
12. Repeat without pressing Power to force a redraw.

Record actual owner confirmation.

If anything fails, use the logs from that exact interaction to identify the cause.

Fix and repeat.

The mission should continue while actionable failures remain.

However, if the phone genuinely requires a kernel modification that cannot be deployed under the no-flash policy, document that blocker rather than looping forever.

---

# 15. RELEASE GATE — v0.5.2-beta

The beta is gated on physical interaction.

Current root version:

`v0.5.1-alpha`

Target:

`v0.5.2-beta`

Prepare release metadata and build changes as needed, but do not claim physically verified beta before owner acceptance.

When the interaction gate passes:

1. Update root `VERSION`.
2. Update active release metadata.
3. Update current PWA version information.
4. Update About Nuxel.
5. Update active package manifests.
6. Update relevant application metadata.
7. Update README.
8. Update CHANGELOG.
9. Update current developer documentation.
10. Update current build instructions.
11. Prepare verified release artifacts.

Preserve historical A33/A34 engineering records.

Do not rewrite historical version references inside old logs.

---

# 16. VERSION NORMALIZATION — CRITICAL FIX

The repository's VERSION file already includes a leading `v`.

Current convention:

`v0.5.1-alpha`

Target:

`v0.5.2-beta`

Inspect `.github/workflows/release.yml`.

A previous review found logic equivalent to:

`tag="v$(cat VERSION)"`

This can produce a malformed tag:

`vv0.5.2-beta`

Fix the version normalization.

The release tag must be exactly:

`v0.5.2-beta`

Support:

- Tag-triggered workflow.
- Manual workflow dispatch.
- Correct source ref selection.
- Correct tag/version consistency.
- Correct artifact naming.
- Correct release metadata.

Do not build one commit and publish the artifacts under an unrelated tag.

Do not automatically push or publish a release without authorization.

---

# 17. UPDATE README.MD

The README must accurately reflect the actual v0.5.2-beta engineering state.

Update:

- Project overview.
- Current version.
- Current hardware target.
- Fedora version.
- Kernel version.
- Real launcher implementation.
- Phoc/WebKit architecture.
- Touchscreen status.
- Application navigation.
- Known remaining hardware limitations.
- Live development.
- Build procedures.
- Release image generation.
- GitHub Actions workflow.
- Testing and verification.
- Recovery and rollback approach.

Don't falsely claim full hardware support.

Don't claim native DRM/KMS graphics acceleration if the S10+ still uses the headless Phoc/framebuffer bridge.

Do not present future Linux 6.x migration goals as already completed.

---

# 18. UPDATE ALL CURRENT DOCUMENTATION

Audit active docs and configuration.

Update relevant:

- Version references.
- Build guides.
- S10+ deployment guides.
- Current software architecture.
- Application lifecycle docs.
- Launcher docs.
- Live-console instructions.
- Release instructions.
- Beta test instructions.
- Current device support matrix.

Create:

`docs/beta-finalization/v0.5.2/`

Include:

- `BASELINE.md`
- `TOUCH-INTERACTION.md`
- `APP-LIFECYCLE.md`
- `TERMINAL-REPAIR.md`
- `GESTURES.md`
- `VIRTUAL-KEYBOARD.md`
- `GUI-RESPONSIVENESS.md`
- `POWER-REGRESSIONS.md`
- `LIVE-DEPLOYMENTS.md`
- `OWNER-ACCEPTANCE.md`
- `VERSION-AUDIT.md`
- `CI-WORKFLOW-AUDIT.md`
- `S10PLUS-BUILD-VERIFICATION.md`
- `KNOWN-LIMITATIONS.md`
- `RELEASE-VERDICT.md`

Use evidence, not optimistic descriptions.

---

# 19. GITHUB ACTIONS — ACTUAL UP-TO-DATE IMAGE BUILDS

This is a mandatory second engineering milestone.

Inspect:

`.github/workflows/release.yml`

and all scripts it invokes.

The GitHub workflow must actually build the latest images from the repository.

Primary target:

**Samsung Galaxy S10+**

Secondary existing target:

**Motorola G7 Power**

Preserve existing supported targets.

Do not silently disable another working build to make S10+ green.

## S10+ artifact requirements

Build:

1. A structurally correct Samsung BOOT image.
2. Fedora 43 ARM64 rootfs.
3. Current userspace binaries.
4. Latest Nuxel PWA assets.
5. Correct application bridge.
6. Correct settings and Terminal code.
7. Current button manager.
8. Current framebuffer bridge.
9. Correct version metadata.
10. Artifact checksums and manifest.

The current release path contains older A25 BOOT engineering alongside newer A34 userspace engineering.

This may be intentional and technically correct.

Do not replace known-working BOOT construction merely because its source directory has an older cycle number.

Verify which stage is authoritative.

Do not introduce an unverified kernel change.

## Clean checkout requirement

The workflow must work without:

- MacBook-specific paths.
- Untracked binaries.
- Preexisting local build outputs.
- Hidden developer caches.
- Running UTM.
- Connected S10+.
- Manually prepared device files unavailable to CI.

Use supported Linux runners and appropriate ARM64 build infrastructure.

---

# 20. SOURCE-TO-IMAGE PARITY

For each runtime-critical component, document:

SOURCE → BUILD → INSTALL PATH → SYSTEMD SERVICE → TEST → IMAGE CONTENT.

Require exact current-source staging.

No stale A27/A28 UI.

No obsolete A32 binaries.

No missing A34 fixes.

No PWA cache serving outdated code.

No duplicate launcher services.

No duplicate framebuffer writers.

No missing Terminal backend.

No incomplete WebKit host deployment.

Verify the final rootfs contents rather than trusting build-script success.

---

# 21. CI TESTING

Perform the strongest available checks.

## Static validation

- YAML syntax.
- GitHub Actions expressions.
- Shell quoting.
- Build matrix.
- Version parsing.
- Artifact references.
- Job dependencies.

## Code validation

- Python syntax/tests.
- C build/tests.
- JavaScript tests.
- Shellcheck or equivalent checks.
- Existing A34 regression tests.

## Clean build

Build the current S10+ image in a clean Linux-compatible environment.

Validate:

- ARM64 ELF architecture.
- Fedora rootfs.
- BOOT image format.
- Initramfs.
- Device-tree packaging.
- Nuxel release metadata.
- Installed PWA.
- Installed bridge.
- Installed services.
- Shared library dependencies.

## GitHub Actions verification

If GitHub access is configured, perform an appropriate nonpublishing verification run.

Record real run IDs, statuses and artifacts.

If hosted CI cannot be run, report it as not verified.

Do not claim GitHub Actions passes merely because YAML parses.

## Publication

Prepare release changes and artifacts.

Do not automatically push a release tag or publish a GitHub Release without explicit authorization.

---

# 22. TESTS TO RUN

Locate and execute existing test suites.

Relevant previous test locations include:

`tools/s10plus/a33/tests/`

`tools/s10plus/a34/tests/`

Look for:

- A34 suite.
- Power/Bixby FSM tests.
- Quick Settings gesture tests.
- Touch SYN translation tests.
- App lifecycle tests.
- Terminal tests.

Add missing tests for:

- Closing the native Terminal window.
- Removing stale overlays.
- Reopening Terminal.
- Switching between applications.
- Returning Home.
- Quick Settings open/close.
- Virtual keyboard input.
- Text-field focus.
- No spurious Back gesture.
- No app traps.
- Power-button navigation isolation.
- Launcher first-frame readiness.
- UI frame presentation.
- Correct installed assets.
- Version normalization.
- CI source-to-artifact parity.

For every test report:

- Command.
- Exit code.
- Revision.
- Actual result.
- Expected result.

Do not fabricate a pass.

---

# 23. AUTONOMOUS WORKFLOW

Use a persistent execution plan.

For each issue:

1. Reproduce.
2. Collect logs.
3. Identify the failing source path.
4. Form a narrow hypothesis.
5. Patch the code.
6. Write or update a regression test.
7. Execute the test.
8. Review the diff.
9. Build the affected component.
10. Deploy if safe.
11. Verify actual runtime behavior.
12. Preserve rollback.
13. Update task status.

Do not repeatedly retry an unchanged failing command.

Do not abandon a solvable issue after one failed attempt.

Do not silently broaden the patch to unrelated components.

Do not continue deploying after losing control of the USB console.

Maintain a concise progress record throughout execution.

---

# 24. REPORTING

At the end generate:

`docs/beta-finalization/v0.5.2/RELEASE-VERDICT.md`

and:

`docs/beta-finalization/v0.5.2/OWNER-ACCEPTANCE.md`

## Engineering report

Include:

- Exact changes.
- Root causes.
- Source files.
- Test results.
- Deployed hashes.
- Runtime observations.
- Remaining defects.
- Build results.
- GitHub Actions results.
- Release readiness.

## Owner report

Include:

- What the owner must physically test.
- Exact actions.
- Expected results.
- Failure symptoms.
- How to gather diagnostics.
- Which tests passed already.
- Which results remain unproven.

Do not report an owner test as passed unless the owner actually confirmed it.

---

# 25. FINAL EXECUTION PLAN

START NOW.

### STAGE A — CURRENT STATE

1. Inspect repository.
2. Read A34 evidence.
3. Inspect phone runtime.
4. Verify deployed files against source.
5. Establish latest baseline.

### STAGE B — TOUCH AND APP INTERACTION

6. Verify actual physical input.
7. Inspect native Terminal lifecycle.
8. Fix stale fullscreen surfaces.
9. Fix PWA app close/home.
10. Fix focus and pointer routing.
11. Fix Quick Settings interaction.
12. Fix virtual keyboard.
13. Fix any UI redraw stalls.
14. Fix Power-button interaction regressions.
15. Execute automated regression tests.
16. Deploy validated changes live.
17. Request physical owner acceptance.
18. Repair remaining failures and retest.

### STAGE C — BETA RELEASE

19. Confirm interaction acceptance.
20. Update `VERSION` to `v0.5.2-beta`.
21. Update active source metadata.
22. Update PWA cache/version metadata.
23. Update README.
24. Update CHANGELOG.
25. Update relevant docs.
26. Audit release workflow.
27. Fix duplicate-v tag handling.
28. Verify latest source inclusion.
29. Build S10+ images cleanly.
30. Validate structural image correctness.
31. Validate Fedora rootfs content.
32. Preserve G7 Power build compatibility.
33. Run all relevant tests.
34. Run hosted CI where authorized and available.
35. Prepare release-ready changes.
36. Produce engineering and owner reports.

---

# 26. FINAL NON-NEGOTIABLE ACCEPTANCE

The user defines beta primarily by actual touchscreen usability.

**REAL FINGER TAP → APPLICATION OPENS.**

**APPLICATION RESPONDS.**

**BACK/HOME WORKS.**

**ANOTHER APPLICATION OPENS.**

**QUICK SETTINGS WORKS.**

**KEYBOARD WORKS.**

**UI UPDATES IMMEDIATELY.**

No Power-button tricks.

No hidden surfaces blocking touches.

No synthetic tests used as substitutes for physical proof.

Then the repository must be release-ready:

**VERSION = v0.5.2-beta**

**README AND DOCS UPDATED**

**LATEST S10+ IMAGE CONTENT VERIFIED**

**GITHUB ACTIONS WORKFLOW REPAIRED AND TESTED**

**NO FLASHING**

**NO UNVERIFIED RELEASE CLAIMS**

## NUXEL v0.5.2-BETA — PULL IT INTO BETA.

The phone already runs Fedora.

It already displays Nuxel.

It already receives physical touch events according to A34 evidence.

**FINISH THE LAST MILE: MAKE THE PHONE ACTUALLY INTERACTIVE.**

Then package the exact tested implementation into a reproducible beta release.

**CODEX GPT-5.4 — EXECUTE. 🐧🔥**
