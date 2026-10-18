# NUXEL — ASTRA TOUCHDOWN / BETA PULLAH
## GPT-6 Astra · Maximum reasoning · Physical S10+ · A real, usable, touch-controlled v0.5.2-beta
### IMPLEMENT → DEPLOY → RUN 90-SECOND OWNER TESTS → DIAGNOSE → REPAIR → VERIFY → BUILD → RELEASE

## 0. THE CONTRACT — THIS IS NOT A REPORT-WRITING MISSION

You are the autonomous lead embedded-Linux, Wayland/Phoc, WebKitGTK, JavaScript/PWA, framebuffer, test-infrastructure, build and release engineer for **Nuxel**, a native Fedora-based ARM64 phone operating system.

**Primary and overwhelmingly highest-priority objective: make the real Samsung Galaxy S10+ screen usable by the owner's actual finger.** It boots Nuxel, displays an increasingly functional GUI, and the physical Power/Bixby/Volume keys trigger recognizable actions, BUT THE OWNER STILL CANNOT RELIABLY TAP APPS, PULL DOWN THE TOP BAR, NAVIGATE, OR TYPE ON THE SCREEN. THIS IS NOT BETA.

At least some older A34 records claim a few genuine physical taps reached WebKit and launched Mail/Calendar. Other older records show charger-mode preventing the touchscreen device entirely, or a native Terminal window remaining above the launcher. These are historical facts to investigate, NOT proof of what is happening in the **present boot and present build**. There has been substantial development since those records. Do not assume the newest code is A34 or that old fixes remain broken; discover current source, runtime, and device evidence.

**Critical distinction: a Bixby/Power/Volume `EV_KEY` event is NOT a touchscreen event.** The phone interpreting hardware buttons does not establish the touch sensor, multitouch `EV_ABS` stream, libinput, WebKit event delivery, or GUI responsiveness.

Desired physical outcome, repeatable with zero special workarounds:

REAL FINGER TAP → CORRECT APP OPENS → VISIBLE FRAME UPDATES IMMEDIATELY → INTERACT → CLOSE/HOME → ANOTHER APP OPENS → SWIPE QUICK SETTINGS → TYPE USING TOUCH KEYBOARD.

Do engineering work, not aspirational planning. A TODO, a source edit, successful compilation, synthesized tap, `apply:false` dry run, or `systemctl active` result does **not** satisfy this contract. Advance to live deployment and real testing where safe. Continue remaining executable work rather than ending after the first diagnosis or first fix. Never fake physical owner verification.

## 1. OPERATING CONTEXT — DETECT THE ACTUAL ENVIRONMENT

- Current engineering host is expected to be the **MacBook M1 Max (macOS, 32 GB RAM)**, with the Galaxy S10+ connected via its USB-C port. Earlier records refer to a Fedora x86_64 laptop (`dextronux`, `/dev/ttyACM0`, repo `/x/nuxel`) which may not be present. Detect actual host, repository, serial device and transport, never hard-code historical Linux paths on macOS.
- Target: **Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820**, Nuxel Fedora 43 ARM64, historically running Samsung Linux 4.14.253. Check current device outputs; don't assume those version strings remain unchanged.
- Authoritative launcher: Nuxel Home PWA under `pwa/nuxel-home/`, historically hosted by WebKitGTK over headless Phoc and mapped to Samsung DECON framebuffer using `nuxel-wl-fb`. Investigate the **currently running implementation** and startup scripts. Do not invent another replacement launcher.
- USB CDC-ACM live console has worked previously, possibly using `scripts/s10plus-debug-pack/nuxel-live.sh`, `nuxel-live-deploy.sh`, or `tools/beta/live/`. Locate and validate the current tools.
- Existing repository task files: `all.md`, `task.md`, `task2.md`, `beta.md`, previous `nuxel-beta-pullah-codex.md`, plus `docs/beta-finalization/`, `docs/s10plus-autonomous-boot-repair/TOUCHDOWN/`, and stage sources `tools/s10plus/a29/` through newer work. Read what's present and identify newer work before writing code.
- Inspect `git status`, current HEAD, branch, VERSION, active work trees, AGENTS.md instructions, pending changes, old task ledgers, latest logs, deployed versions and version history. Do not overwrite work from an active concurrent engineer.
- Development goal **`v0.5.2-beta`**. Do not assume the current source still says `v0.5.1-alpha`: read it.

## 2. AUTONOMOUS EXECUTION, PRIORITY AND EVIDENCE

At launch, create/update a durable, dependency-ordered task ledger, preferably under `docs/beta-finalization/v0.5.2/ASTRA-TOUCHDOWN-TODO.md` and JSON, plus `RESUME.md`. If a newer authoritative ledger already exists, **reuse it** and cross-link instead of resetting statuses. Preserve old data. Keep a top-of-file live summary with: current phone reachability, current boot mode, first failing input stage, deployed revision, owner test state, next executable action, build state, release gate.

Priority order:

**P0: LIVE TOUCHSCREEN USABILITY.** Diagnose → implement → live deploy → 90-second owner trials → inspect → repair → repeat until proven or until a precisely evidenced safety/kernel barrier forbids live repair.

**P1: Related graphics/app interaction.** App lifecycle, invisible top-level surfaces, touch-to-click translation, gesture routing, virtual keyboard, system UI redraw, wallpaper-first-frame startup, correct Power/Bixby handling.

**P2: Stability/regression and deployment parity.** Ensure fixed files are actually installed, loaded and exercised; preserve rollback and a functioning live console.

**P3: Beta release engineering.** Version `v0.5.2-beta`, README/changelog/current docs, current clean S10+ BOOT+rootfs image build and hosted CI; preserve G7 build, honest hardware limitations, commit/push/tag/release only at verified gates.

**P4: Remaining tasks from task.md/task2.md.** Review and complete safe, independent still-open items after P0 is solved or genuinely blocked. Do not allow modem/Flatpak/feature breadth to distract from the owner's non-clickable phone.

For every fix store evidence: problem, target revision, source file, change, test command/exit code, artifact hash, deployed hash, service restart, console receipt, observed physical result, rollback and status. Statuses: `NOT_STARTED`, `IN_PROGRESS`, `OFFLINE_TESTED`, `DEPLOYED`, `RUNTIME_VERIFIED`, `OWNER_VERIFIED`, `OWNER_TEST_REQUIRED`, `BLOCKED_KERNEL`, `BLOCKED_ENVIRONMENT`, `FAILED`, `DEFERRED`. Avoid marking something `OWNER_VERIFIED` from an automated event alone.

**No fake “one run lasts forever” promises.** Keep working while tools and actionable work are available. Persist checkpoints before context or usage interruptions. If the agent process ends because of session/usage/tool limits, leave an exact resume instruction and next command. If further progress requires an absent owner or unpermitted kernel change, finish independent tasks and report that specific limitation; don't invent a pass or infinitely retry the same command.

## 3. NON-NEGOTIABLE HARDWARE PROTECTION

The MacBook and the running phone are valuable. Full-host Codex permissions are not permission for destructive commands.

**NEVER** flash BOOT, USERDATA, RECOVERY, SYSTEM, DTB, DTBO, VBMETA, modem or other partitions; never run Heimdall/Odin, write raw block devices, repartition, modify EFS/IMEI/PIT/calibration, change bootloader state, enter Download/TWRP mode, deploy an unverified kernel/kernel module, or trigger unattended recovery. Rebuild images **offline** as needed; never flash them.

Permitted: read-only kernel/source diagnostics, safe userspace source changes, properly target-built Linux AArch64 binaries, PWA/CSS/JS fixes, service/udev configuration if safe, targeted process/service restarts, safe atomic userspace deployment with verified rollback, and normal reboot back into Nuxel **only if actually necessary and current console/recovery conditions are understood**. Bounded normal reboots, not trial-and-error loops. Preserve USB console access; one serial-port owner at a time. For macOS verify serial access and identify `/dev/cu.*` dynamically. A blank or byte-silent console does not prove the phone is dead; change diagnostics and check USB re-enumeration.

Before any phone write: read fresh running device identity, kernel cmdline, service state, input device inventory, current process/version/asset hashes, free space and storage health. Capture known-good backups and test rollback for files to be replaced. For each deployment: compile for correct Linux ARM64 ABI (do not deploy Mach-O), hash staged and destination files, atomic install, restart smallest service, verify frames/logs/clickability, rollback if regression.

Do not run multiple framebuffer owners or serial-console clients. Do not use an evdev exclusive grab as a passive observation tool. Never dump secret-bearing logs, SIM identifiers, personal data, tokens or IMEI to a public repository. If uncertain about a dangerous step, stop that step and continue safe work.

## 4. FIRST 15 MINUTES: PROVE WHAT ACTUALLY FAILS

Before proposing repairs, determine which of these are **freshly observed**, not merely historical:

A. Physical touchscreen `sec_touchscreen` registered; normal vs `androidboot.mode=charger` / `lpcharge=1` state.
B. Finger contact changes IRQ counter (if exposed).
C. A physical touch produces correctly grouped `ABS_MT_TRACKING_ID`, `ABS_MT_POSITION_X/Y`, `BTN_TOUCH` (if present), `SYN_REPORT` on the expected input event node.
D. libinput classifies and receives physical touchscreen contact.
E. Phoc seat and output receive physical touch; its output mapping/focus is correct.
F. WebKit GTK receives an actual Wayland touch; DOM sees `pointerdown`/`touchstart`/`pointerup`/`click` with target, coordinates and current window state.
G. Correct application handler fires and backend/window lifecycle succeeds.
H. A newly rendered UI frame reaches Phoc screencopy and Samsung framebuffer promptly, with no Power-button-triggered redraw needed.
I. Real finger can repeatedly open, interact, close, navigate and type; owner explicitly confirms.

**The first unproven or failing link is the debugging target.** Do not assume C–I merely because Power/Bixby keys reach userspace. Do not rewrite the Samsung driver when C/D work. If C/D genuinely fail, investigate current `sec_ts` startup, correct boot mode, runtime power/suspend, touch-arm helper and safe ioctls. Inspect Linux UAPI from the target; never guess ioctl numbers, offsets or register values. If the compiled-in driver is absent due to charger boot, follow the documented bounded normal-boot recovery; don't pretend a userspace fix can recreate a driver skipped at kernel init. If a kernel change is the only remedy, produce offline patch and a `BLOCKED_KERNEL` verdict, not an unsafe deploy.

Pay special attention to this historical defect list, but validate present code/runtime before reopening a resolved issue:

1. A34 had a new multitouch contact processed before its X/Y fields were committed at SYN_REPORT, resulting in false Back/edge gestures.
2. A native Terminal/PTY window remained foreground after logical close, invisibly blocking the launcher. Investigate actual `term_close_window()` and the current window lifecycle.
3. PWA `NuxelLauncherClose()` / iframe cleanup / parent host bridge could be absent or stale.
4. Fullscreen splash `<video>`/invisible overlay could intercept input after visual dismissal.
5. Incorrect Wayland logical scale, rotation, output transform, raw ABS-to-screen calibration or camera cutout may cause hit tests outside icons.
6. WebKit GTK/Phoc may have missing seat/touch event delivery, incorrect focus or input permissions, or a libinput/udev compatibility issue.
7. Pointer+touch compatibility handlers may double fire or suppress click incorrectly; `touch-action`, passive listeners, capture, z-index and CSS `pointer-events` may be wrong.
8. Missing app backend/bridge may open an empty dark full-screen app which looks frozen; ensure error/empty state and a reliable Close/Home path.
9. Launcher may be responsive internally but presentation updates only after Power events. Check Phoc Wayland frame callbacks, screencopy, stale damage, framebuffer pan ownership, and UI main-loop blocking.
10. Rootfs may run **older installed assets/binaries** than the latest source because previous deploy manifest missed the actual app set, files were only staged or the PWA service-worker cache still serves old JS.
11. Power/Bixby double-press logic may misroute an action to Terminal; short Power must not open Terminal or be needed to redraw UI.

Compare competing hypotheses with a **single real physical tap** captured at every available stage, timestamp-correlated. Put definitive diagnostics into small tools/tests rather than continuously accumulating debug output. Investigate real output focus/stacking and trace the currently visible app. Use direct evidence such as target `elementFromPoint` + `composedPath` and real displayed state, not unsupported speculation. Do not let logging inadvertently swallow input or block the WebKit main thread.

## 5. THE OWNER'S 90-SECOND LIVE TEST WINDOWS — MANDATORY

The owner is standing by with the phone. **Do not simply ask them to check later.** Run an active capture-and-analysis workflow and continue automatically after each timed window.

Use the currently working framed USB live console to **arm a bounded phone-side capture**, ideally via a transient systemd service or existing diagnostic test mechanism that survives release of the serial port and terminates automatically after **90 seconds**. Collect touch evdev, relevant compositor/WebKit input markers, active application/window state and frame-presentation events where feasible. Do not hold the serial-port lock idle throughout the 90 seconds if the owner needs the port for other tools. Ensure logs are retrievable after the window, have accurate time bases and bounded size, and do not include secrets. If setting up the recorder is not possible, use an equally safe on-host/phone logging strategy with an explicit deadline and proven capture.

**For every test window, perform this exact interaction protocol:**

1. Prepare tracing, capture current stage readiness, verify free space, set strict timeout and recovery.
2. Print an extremely visible, unbuffered terminal message **before** starting, such as:

   `===========================================================`
   `NUXEL — LIVE TOUCH TEST 1 — STARTING NOW (90 SECONDS)`
   `PLEASE TOUCH THE PHONE NOW. You have 90 seconds.`
   `DO THESE ACTIONS: [exact 2–5 short actions appropriate to this test]`
   `I AM RECORDING EVENTS; YOU DO NOT NEED TO TYPE ANYTHING.`
   `===========================================================`

   Ring the terminal bell if useful (`printf '\a'`), but don't depend on audio. Show deadline/countdown (e.g., updates at 60, 30, 10 seconds if practical). Output through stderr/stdout in a way the user can actually see while Codex runs; do not bury the prompt inside JSON events. Don't start counting before capture is armed and owner instructions are visible.
3. Allow **90 full seconds** for the user to physically tap/swipe. A real `timeout 90` capture, controlled sleep, or phone-side timer must do the waiting. The agent must **not** summarize prematurely because nothing arrived after five seconds. Avoid passing beyond the timeout silently. Do not issue unrelated deploy/restart/reboot commands during capture.
4. After 90 seconds, close the capture, automatically retrieve the logs, correlate the real finger events across layers, compute a factual verdict, and **continue diagnosing/patching/deploying** without waiting for another chat prompt.
5. If input was absent, distinguish `NO_PHYSICAL_EVENT_RECORDED`, `INVALID_CAPTURE`, `CAPTURE_BLOCKED`, and `EVENTS_RECORDED_BUT_NOT_FORWARDED`; no invented user actions. If owner explicitly says they tapped but there are no events, that is a test failure with a known observation, not a pass.
6. Repeat a fresh 90-second test only after changing code or isolating a new hypothesis. Limit redundant owner interactions; combine actions into 2–3 logically structured sessions when feasible.

### WIN 1 — RAW FINGER CONTACT (90s)

Prompt owner: **"With Nuxel visible, tap the CENTER 5 times, tap the SETTINGS icon 3 times, then swipe from the TOP down and from the BOTTOM up. Repeat slowly. You have 90 seconds; start now."**

Goal: irrefutable present-boot physical `ABS_MT_*` timestamps, positions and complete `SYN_REPORT` frames, with libinput/Phoc/WebKit correlation where available. If nothing reaches evdev, debug kernel/touch state first. If events reach WebKit but handlers don't work, switch to DOM/surface debug immediately. If handlers work but GUI doesn't refresh, switch to presentation.

### WIN 2 — INTERACTION AFTER TARGETED REPAIR (90s)

Only after deploying the next validated fix, prompt owner:

**"Tap Settings and Close; open Calendar and return Home; drag down Quick Settings and close it; tap the search field and type NUXEL using the onscreen keyboard. Repeat if time allows. You have 90 seconds; start now."**

Goal: open/close/navigation/gesture/input/render actions, no Power key involved. Capture both backend state changes and visible frame receipts. Do not treat app launch logs without an actual shown app as acceptance.

### WIN 3 — STABILITY / BUTTONS / REPEATABILITY (90s)

After WIN 2 has no reproducible blocker, prompt owner:

**"Open and close two different apps twice, scroll in one app, use Back/Home, then press Power once to turn screen off and once to wake; do not double-press it. Report whether everything moved visibly as expected. You have 90 seconds; start now."**

Goal: persistence, no invisible windows, no ghost clicks, no Power-triggered Terminal, frame progression, wake/blank consistency. Never ask to trigger Download or Recovery mode.

### OWNER VERIFICATION IN A NON-INTERACTIVE `codex exec`

A headless Codex turn cannot magically read the owner's thoughts or wait for an interactive reply. Implement an **actual local owner feedback channel**: create a small, clearly labeled, ignored/local file such as `docs/beta-finalization/v0.5.2/owner-feedback.local.txt` and print a copy-pastable command for a **second terminal**. During or just after WIN 2/WIN 3, owner can write e.g.:

`printf '%s\n' 'WIN2 PASS: Settings, Calendar, Quick Settings and touch keyboard all worked visibly' >> docs/beta-finalization/v0.5.2/owner-feedback.local.txt`

or:

`printf '%s\n' 'WIN2 FAIL: Settings opened but Home did not return' >> docs/beta-finalization/v0.5.2/owner-feedback.local.txt`

Read that file only after the test deadline, check it was updated by the owner in the applicable test window, and record owner confirmation separately from machine logs. The agent must never fabricate/write its own PASS feedback. Make sure the path is ignored by Git and contents are never committed automatically. If owner doesn't provide feedback, classify as `OWNER_TEST_REQUIRED`; finish source/build work instead of blocking forever. Do not claim release verified without explicit positive physical owner feedback.

For interactive Codex (not `exec`), you may ask the owner for the test result directly once the timed capture completes; still keep the phone-side capture and real 90-second wait.

**After every test window, automatically inspect results and proceed to the next repair.** Do not end the mission with “please perform test later” when the phone, owner and diagnostics are ready now.

## 6. ACTUAL DEPLOYMENT — NOT ANOTHER DRY RUN

Historical records in `task2.md` document a prior result with `"apply":false`, `"results":[]`, 37 steps in seven groups, and `IMPLEMENTED_NOT_DEPLOYED`. Treat these as a warning, not as the current state. The current repo may now contain more comprehensive deployment tooling, services and packages; inspect it first.

- Map exact *running phone* component → source commit → build script → output file → installed path → active service/URL → captured live test.
- If required fixes are already in source but not on phone, prioritize bringing the active runtime into sync safely rather than rewriting them.
- For JS/CSS assets, check file hashes, served URL, MIME type and service-worker cache; force correct cache invalidation through supported mechanisms rather than just rewriting version text.
- For C/C++ components, verify Linux AArch64 ELF and all target dependencies; macOS arm64/Mach-O is NOT compatible with Fedora ARM64.
- Inspect existing deploy manifest coverage. Extend only as needed to include present-version PWA, native host, button manager, libinput shim, framebuffer bridge, user services, app bridge and relevant configs. Never blindly overwrite newer code with older A34 bundles.
- Run validation/dry-run to check safety, **then apply the actual authorized userspace changes**, verify target hashes, service state and observable functionality. `--apply` should be used only when its current semantics are known, guards are satisfied and rollback exists.
- Single serial owner, retries bounded; preserve one verified console recovery path throughout.
- After every successful deployment, run a 90-second owner test when physical input is needed. Test results drive the next iteration.

## 7. FIX THE COMPLETE INPUT/INTERACTION CONTRACT — NO NEW LAUNCHER

The current Nuxel Home must remain the shell. Implement the minimum changes necessary so:

- App icons always respond to one tap; no double-tap requirement.
- App appears visibly; blank/error states have title, usable Close/Home and clear status.
- Close actually destroys/hides the top-level native or iframe surface and returns touch focus to Home.
- Launcher scroll and app scrolling work without false edge gestures.
- Status-bar pull-down opens Quick Settings, upward/dismiss action closes it. Distinguish a missing gesture handler from a lost physical event.
- Current OSK appears on text focus, sends real text into the focused field, and dismisses; test in Search and Terminal if Terminal backend exists.
- Touch coordinate transform, display scale and panel orientation match the actual current output.
- No invisible transparent modal, boot splash, frame or stale native window captures touches; keep a recovery-safe Home path.
- GUI presents each state change promptly; button/volume overlay doesn't wait for Power events; initial launcher appears after boot without needing double Power.
- Single/double/long Power and Bixby do not cross-fire; short Power blanks/wakes exactly once, long Power shows a safe menu if supported; hardware buttons are regression tests, NOT touch proof.
- Restarted services recover with correct compositor seat/focus without destroying the USB live console.

Tests: current repo unit tests (including any A33/A34 touch-SYN, Quick Settings, power FSM and display bridge suites), narrow new regression coverage, app lifecycle and close/reopen tests, compositor/bridge diagnostics, post-deploy live checks, and explicit owner physical acceptance. Collect actual command receipts. No synthetic tests substituted for the owner's finger.

## 8. AFTER P0: COMPLETE BETA ENGINEERING AND REAL RELEASE BUILDS

When P0 physical usability is owner verified **or** only an evidenced no-flash kernel blocker remains, proceed through every independent safe executable task from `task.md` and `task2.md` in priority order, checking against the latest source and runtime. Do not let unrelated unfinished modem/camera hardware prevent the explicitly scoped **touch-usable beta**; document missing hardware truthfully as known limitations.

**Target `v0.5.2-beta`** only after current owner-confirmed usability. Prepare release metadata/docs ahead of time where practical, but don't stamp a nonexistent physical success. Inspect current VERSION first and normalize tags without duplicate `v` (a prior workflow did `v$(cat VERSION)` despite VERSION already containing `v`). Update root VERSION, active PWA/about/package metadata, service worker cache names, README.md, CHANGELOG.md, current build/release docs, capability matrix and relevant active docs. Preserve historic A29–A34 reports and older release lines unchanged.

Audit `.github/workflows/release.yml` and all invoked build/package/verification scripts. **The S10+ release rootfs must include the exact current touch/GUI/userspace bits tested live**, not obsolete A27/A32/A34 source copies or hidden MacBook build outputs. Preserve historically verified A25-style Samsung BOOT structure if it remains authoritative; verify kernel+initramfs+DTB structural requirements without flashing. Fedora 43 ARM64 ext4 image must have working `/sbin/init`, correct ELF ABI/dependencies, active Nuxel Home, latest host/bridge/button/touch components, all required app assets, appropriate service-worker cache, current service files and matching manifest. Verify device- and source-to-artifact hashes/provenance; flag any runtime-only local modifications not represented in the committed source/build.

Build from a fresh checkout and clean Linux-compatible build host/container, not presumed Mac-specific state. Preserve and test existing G7 Power release path if current CI supports it. Run structural verification, complete tests, checksum generation, workflow YAML validation and a real hosted GitHub Actions verification job when authenticated access exists. Report actual CI run URL/status, not merely a successful local workflow parse. Fix tag/branch checkout mismatch and double-v version bug. Avoid exposing secrets in artifact manifests.

The owner previously authorized normal git add/commit/push and official tag/release for this verified release. However, **the official `v0.5.2-beta` tag/public GitHub release is CONDITIONAL** on positive owner finger verification, no hard failing release gates, successful image verification/hosted CI and tag/commit/version consistency. Do not force-push, overwrite tags, publish a half-built image, or launch duplicate release jobs. You may commit/push a clearly marked work branch for unfinished work when safe. If publication requires credentials or CI hasn't passed, report the precise blocker and leave ready-to-run commands. If everything passes, commit, normal push, tag/push once, monitor the release workflow and check assets/checksums and exact source commit.

## 9. FINAL ARTIFACTS AND TRUTHFUL VERDICTS

Maintain:

1. `docs/beta-finalization/v0.5.2/ASTRA-TOUCHDOWN-TODO.md` plus machine-readable progress ledger.
2. `docs/beta-finalization/v0.5.2/RESUME.md` with last working command, exact block, next action, and target runtime state.
3. Current input-ladder event trace showing real physical contacts at each verified stage.
4. Three 90-second capture receipts with timestamps/exit codes (where executed), owner feedback as a **local, uncommitted** record.
5. `TOUCH-ROOTCAUSE.md` documenting the first broken layer and proven fix or specific blocker.
6. `LIVE-DEPLOYMENTS.md` with real installed hashes/rollbacks; no plans misrepresented as deployments.
7. `OWNER-ACCEPTANCE.md` with supported physical owner statements and `NEEDS_OWNER_TEST` where absent.
8. `BETA-RELEASE-VERDICT.md` with current build, CI, tag and actual phone evidence.
9. Current-version README, CHANGELOG, active docs and source-to-image manifest when the gate is met.

Before finishing ANY turn, re-read the TODO and ask:

- Is there a safe, actionable task left that will get finger-clickability closer? If yes, do it now.
- Is the phone reachable and the patch safe to install? If yes, deploy and verify rather than ending at a build.
- Is a test window armed and the user available? If yes, finish the actual 90-second wait and capture.
- Are independent release-source/build tasks still executable? If yes, continue those while awaiting physical confirmation.
- Is owner approval/evidence genuinely missing? If yes, document it as a specific gate, not success.

Only final success states permitted:

- `NUXEL_V0_5_2_BETA_OWNER_VERIFIED_RELEASED` — actual owner finger success, installed parity, clean CI and release published.
- `TOUCH_OWNER_VERIFIED_RELEASE_PENDING` — real finger usability confirmed; release/build not yet ready.
- `TOUCH_RUNTIME_REPAIRED_OWNER_CONFIRMATION_PENDING` — actual current physical event/action evidence, but no owner confirmation.
- `TOUCH_PARTIAL_FIRST_FAILING_LAYER_IDENTIFIED` — specific demonstrated broken step and next fix.
- `TOUCH_BLOCKED_KERNEL_NO_FLASH` — precise kernel-only defect with offline repair path.
- `BLOCKED_DEVICE_OR_TOOLS` — exact unavailable capability, no fake pass.

**ABSOLUTELY NEVER call beta complete because hardware Power/Bixby events register, a test binary passes, a WebKit log says `app:launch`, or a GUI screenshot looks correct.** The owner's finger must reliably operate Nuxel, and the owner must say so.

## 10. START EXECUTION NOW — DO NOT SPLIT INTO ANOTHER MISSION

1. Print brief current mission state.
2. Detect host, git HEAD, current version and source/runtime mismatch.
3. Locate/verify USB live console with one owner, framed receipts, current boot mode and `sec_ts` state.
4. Arm **90-second WIN 1**, show clear instructions and wait the entire interval while recording real events.
5. Analyze the first broken touch layer; implement minimal repair, test, build correct architecture, live-deploy safely.
6. Arm **90-second WIN 2**, record tap/close/swipe/keyboard behavior and frame presentation. Read owner feedback if provided.
7. Continue repair/test iterations; run **90-second WIN 3** after meaningful fixes for stability and buttons.
8. Iterate until owner can control the phone or a precise, evidenced prohibition/kernel issue prevents live repair; do not silently backslide into source-only claims.
9. Then complete regression, repository TODO reconciliation, documentation, version and clean S10+ images; validate hosted CI and official release gates.
10. Persist detailed checkpoints and final truthful verdict. If resumable work remains and tools are functional, keep doing it.

**NOW: STOP DIAGNOSING BIXBY/POWER AS TOUCHSCREEN SUCCESS. PUT REAL FINGERS ON THE GLASS, RECORD THE COMPLETE PATH, FIX THE FIRST BROKEN LAYER, AND PULL NUXEL INTO ITS FIRST ACTUALLY USABLE v0.5.2-beta.**
