# FULL-PWNAGE-88000 — Operation Zero-Flash, Heard Doom, Real Services & Living Spoof

## The complete source-led implementation, repair, deployment and physical-verification specification for Nuxel on the Galaxy S10+

**Target device:** Samsung Galaxy S10+ `SM-G975F`, codename `beyond2lte`, Exynos 9820, ARM64  
**OS:** Nuxel / Fedora Linux 43 aarch64 mobile rootfs  
**Known kernel baseline:** downstream Samsung Exynos 9820 tree, Linux `4.14.253-gf7194c1d15ed-dirty` (re-discover on the live phone; do not assume it is unchanged)  
**Repository:** `/Users/wicked/x/nuxel` (phone equivalent normally `/root/nuxel` or the repository checkout used by the deploy helper)  
**Branch at prompt-authoring time:** `pwnage-80000`  
**Primary access:** Wi-Fi SSH to the Nuxel root console with the owner key `~wicked/.ssh/wicked_wqn_id_rsa`  
**Round:** PWNAGE-88000  
**Companion analysis:** `docs/pwnage-88000/DEEP-ANALYSIS.md` — read it first; this document turns its findings into mandatory work.

---

# 0. Mission command and definition of done

Execute the complete specification. This is not a planning exercise, a mockup, a UI-only patch, or a request to write a new plan that leaves the device unchanged. Inspect the current source and the actual running S10+ first, reproduce each reported failure, find the real root cause, implement the fix across every necessary layer (PWA, native chrome, compositor/bridge, systemd, launch profiles, packaging and settings), deploy narrowly with backups, and prove the result on the physical handset.

The owner explicitly asks for **all** of the following. Treat every line as a required outcome, not a suggestion:

1. Eliminate the 1–2 s of zoomed-in desktop visible before the real lockscreen when the screen is powered on.
2. Fix Nuxel Doom audio; it must start with sound on by default and produce real sound effects and music.
3. Set up and configure Waydroid, install ServiceNow Mobile Agent, Microsoft Authenticator and Aegis Authenticator inside it, and honestly test whether each works.
4. Never display app content behind the triple buttons while they are open; when they close, the app must reoccupy that space. Apply the same rule to the collapsing/expanding top bar.
5. Fix the timer so it counts down smoothly, not sluggishly.
6. Move the lockscreen timer penguin to the horizontal center and vertically over the wallpaper penguin.
7. Fix the case where an app is invisible but still owns the foreground, so the Applications drawer cannot open; holding Back to kill it is not an acceptable primary workaround.
8. Allow timers shorter than one minute; ensure they display and run correctly instead of becoming `0:00`.
9. Remove the occasional second timer penguin appearing above the original when the timer goes off.
10. Make the timer penguin shake heavily when it goes off.
11. Move the lockscreen alarm penguin to the horizontal center, below the timer penguin placement (just below the wallpaper penguin and above the lock/unlock penguin), and make it shake heavily when it goes off.
12. Ensure alarms only fire when enabled; the current On/Off behavior appears reversed.
13. Ensure an enabled alarm actually shows its penguin before it rings, not only while ringing.
14. Make Nuxel measurably smoother with evidence-backed performance changes.
15. Minimize boot time further with measured, safe changes.
16. Make `nuxel-preloading-screen.mp4` play its full 6.016 s clip again; no early cut, freeze, static poster, or hidden playback.
17. Add a Services section to Settings with enable/disable/start/stop/reload/restart controls, `systemd daemon-reload` and `daemon-reexec`, protected by an explicit unlock button; mark all system-essential services that can break functionality when stopped.
18. Fix the 1–2 s zoomed-in desktop flash again from the physical Power-button wake path (the same defect as item 1; it must be proven fixed, not merely patched in one layer).
19. In Flatpak and native GTK+ apps, make the bottom triple-button strip reveal on swipe-up and hide on swipe-down; make the top bar reveal on swipe-down and hide on swipe-up. This must work in messenger apps. Remove the extra bottom stripe that clashes with the native affordance.
20. Make PenguInterface able to show the current user agent, spoof the user agent, spoof `/etc/os-release`, spoof `uname` output, and use `LD_PRELOAD` for app-scoped spoofing like the owner's Fedora-laptop work in `./spoof`; add a reset button that removes all spoofs.
21. Make GTK+ and Flatpak apps respect Adwaita-dark (Archive Manager, Firefox, etc.) instead of remaining light.
22. Fix DevMgmt tab text overlap and make tabs horizontally scrollable without a visible scrollbar.
23. Make the Nuxel Browser and Mozilla Firefox properly responsive on the S10+.
24. Make future apps installed through the Software app work immediately and responsively without per-app flags or manual investigation.
25. Make desktop app icons draggable to another grid cell; add a Move button to the icon action row (currently Resize/Remove/Home settings/Done), replace Home settings with Move, add a button showing the current desktop number that opens a desktop picker/switch, and do the same for widgets.
26. Nuxel Doom: always start with sound enabled and working; move Use, −, +, Map and Menu to the top-left/top-right instead of centered above the Doom HUD; increase default aim sensitivity to 3×; make Use, −, +, Map and Menu actually work.
27. Fix any other real defects found by the deep analysis, without turning this into an uncontrolled rewrite.

## 0.1 Definition of done

A workstream is done only when all of the following are true:

- The real root cause is documented with source and live evidence.
- The implementation is in the repository and deployed to the actual S10+ where applicable.
- Focused automated tests pass, including new regression tests for every repaired contract.
- The behavior is verified physically on the handset (audible sound, visible frames, actual touch, actual service state, actual app launch), or is explicitly marked `BLOCKED_*` / `NEEDS_OWNER_TEST` with the exact blocker and what was still verified.
- No required existing behavior regressed: boot, recovery, Wi-Fi SSH, touch, Phoc/Wayland, `nuxel-wl-fb`, audio routing, lock/unlock, launcher, Flatpak sandboxing, orientation, camera, storage, or user data.
- A timestamped backup, hash manifest, evidence bundle and tested rollback exist.

Do not declare success because a file exists, a daemon returned HTTP 200, a CSS class was applied, or a screenshot shows a label. Prove the physical outcome.

## 0.2 Absolutely forbidden shortcuts

- Do not fake Waydroid, spoofing, audio, service control, app launch, gesture input, frame playback, or hardware state.
- Do not replace the real Chocolate Doom WASM engine with a mock/raycaster or remove its WAD catalogue.
- Do not add a second `/dev/fb0` writer. `nuxel-wl-fb` remains the sole framebuffer owner during the Wayland session.
- Do not stop, disable, restart or re-exec systemd or essential Nuxel services without the safety procedure in this document.
- Do not apply `LD_PRELOAD`, spoofed `/etc/os-release`, or spoofed `uname` globally to the bridge, Phoc, `nuxel-wl-fb`, systemd, root shells or unrelated system services.
- Do not store credentials, MFA seeds, session cookies, tokens, private keys, or personal data in source, logs, command arguments, evidence, screenshots or screenshots of Android apps.
- Do not install random APKs, enable unknown repositories, or bypass Play Integrity/SafetyNet in a way that harms the owner's accounts.
- Do not flash kernel, boot, recovery, super, userdata, or repartition anything for these userspace defects. A kernel change for Waydroid is a separate, explicitly approved safety gate.
- Do not use `StrictHostKeyChecking=no`, delete host keys, print private-key contents, or silently fall back to USB/serial when Wi-Fi SSH fails.

## 0.3 Mandatory Wi-Fi root connection

From the repository root:

```bash
cd ~/x/nuxel
KEY=~wicked/.ssh/wicked_wqn_id_rsa
test -r "$KEY" || { echo "OWNER SSH KEY MISSING"; exit 1; }
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --status --user root --key "$KEY"
```

Discover the current phone WLAN address. Historical values such as `192.168.178.167` are hints only. Open the root console through the same helper:

```bash
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_WLAN_HOST" \
  --user root --key "$KEY" --shell
```

Verify:

```bash
id -u                 # must be 0
uname -a
cat /etc/os-release
getprop 2>/dev/null | head -20 || true
boot_id=$(cat /proc/sys/kernel/random/boot_id)
uptime
```

If Wi-Fi SSH is unavailable, preserve the exact diagnostic, continue only with source-side work, and mark every physical acceptance item unverified. Do not claim a device result without a live session.

## 0.4 Execution principles

- **Live state wins.** The repository is on `pwnage-80000` with many uncommitted changes. The phone may be newer than the checkout. Before editing, compare `git status`, `git diff`, deployed hashes, running processes, unit files and state documents. Never overwrite newer live work with an older ZIP, backup or prompt version.
- **One owner per concern.** Lockscreen lock state, timer scheduling, display blanking, process launch and service control each need a single authoritative owner. Do not add a second scheduler, second dock, second top bar, second framebuffer writer, second preload controller or second collision model.
- **Fail closed for security and fail open for presentation.** A lock or service-danger operation must fail closed; a boot video failure must reveal the real lockscreen within a bounded time.
- **Measure before and after.** Capture frame timing, CPU/RSS, wakeups, launch times, boot timings and audio state. Revert any performance change that does not improve the measured target or that adds risk.
- **Atomic writes and narrow restarts.** Stage to a temporary path, verify SHA-256, atomically install, set owner/mode, restart only the affected unit, and verify state.
- **No hidden state.** Every change to a user-visible setting or service must have a persisted document, a readback and a reset path.

---

# 1. Mandatory reconnaissance before any edit

## 1.1 Repository state

```bash
cd ~/x/nuxel
git status --short --branch
git log -8 --oneline --decorate
git diff --stat
find docs -maxdepth 3 -type f \( -iname 'ENGINEERING-REPORT.md' -o -iname '*PWNAGE*REPORT*' \) | sort | tail -100
```

Read:

- `docs/pwnage-88000/DEEP-ANALYSIS.md`
- `docs/pwnage-87000/evidence/LATEST` and the referenced engineering report
- `docs/app-responsiveness-20261107/ENGINEERING-REPORT.md`
- `docs/pwnage-85000/evidence/20261106T162408Z/ENGINEERING-REPORT.md`
- `docs/pwnage-80000/REPORT.md` and any later report
- `README.md`, `docs/building.md`, `docs/build-guide.md`, the S10+ bring-up doc and the live SSH helper README

Locate the real deployed paths. Do not assume `/usr/libexec/nuxel/nuxel-clockd` or `/usr/share/nuxel/pwa` without `systemctl show`, `readlink -f /proc/<pid>/exe` and the image builder.

## 1.2 Live baseline dossier

Capture, without secrets:

```bash
uname -a; cat /etc/os-release; cat /proc/sys/kernel/random/boot_id; uptime
cat /proc/cmdline
systemctl --no-pager --failed
systemctl --no-pager --full list-units --type=service --all | sed -n '1,240p'
systemctl --no-pager --full list-unit-files --type=service | sed -n '1,260p'
ps -eo user,pid,ppid,comm,args --sort=-%cpu | sed -n '1,120p'
systemd-analyze time 2>/dev/null || true
systemd-analyze blame 2>/dev/null | sed -n '1,80p' || true
systemd-analyze critical-chain 2>/dev/null | sed -n '1,120p' || true
```

For every Nuxel unit that will be touched:

```bash
u=nuxel-wayland.service
systemctl cat "$u"
systemctl show -p Id,Description,LoadState,ActiveState,SubState,UnitFileState,FragmentPath,ExecStart,User,Group,Environment "$u"
```

Capture display/input/audio/lockscreen truth:

```bash
cat /run/nuxel-wl-fb.state 2>/dev/null || true
cat /var/lib/nuxel/display 2>/dev/null || true
cat /run/nuxel/security/lock-state.json 2>/dev/null || true
cat /run/nuxel/clockd.state 2>/dev/null | head -c 20000 || true
cat /run/nuxel-navdock.json 2>/dev/null || true
cat /run/nuxel-statusbar.state 2>/dev/null || true
cat /run/nuxel/preload-cinema.overlay 2>/dev/null || true
cat /run/nuxel/preload-cinema.receipt 2>/dev/null || true
cat /run/nuxel/foreground.state 2>/dev/null || true
cat /proc/bus/input/devices
```

Capture installed packages and Flatpak state without dumping secrets:

```bash
rpm -q flatpak waydroid firefox file-roller gnome-themes-extra adwaita-icon-theme 2>/dev/null || true
flatpak --version 2>/dev/null || true
flatpak list --app --columns=application,arch,branch,origin,installation 2>/dev/null || true
flatpak list --runtime --columns=application,arch,branch 2>/dev/null || true
flatpak remotes 2>/dev/null || true
```

## 1.3 Reproduce every symptom before patching

Create a reproducible checklist and record it in the evidence bundle:

- Wake flash: record the panel from the physical Power press at 0/100/250/500/1000/2000 ms; capture `nuxel-wl-fb` state, `lock-state.json`, Home class changes, and `foreign-toplevel list` at each step. Test with the phone locked and unlocked, after idle blank and after a Power-button blank.
- Triple buttons/top bar: test from Home, Archive Manager (GTK), Signal or another Electron/Flatpak messenger, Telegram, Firefox, and a PWA. Record touch start/end coordinates, direction, whether the strip appeared, and whether the app kept input.
- Timer: set 5:00, 0:30, 0:05; observe display cadence for 5 s; trigger expiry; count visible timer penguins and DOM nodes.
- Alarms: create disabled, enabled one-shot, enabled recurring; check indicator before due, toggle state, fire state, and post-fire state.
- Invisible app: reproduce with the owner's normal sequence, then capture `appSession`/`data-app-state`, iframe rect/computed style, foreign-toplevel inventory, and Back/history state.
- Doom: fresh launch with cleared test profile and with the owner's current profile; capture engine argv, AudioContext state, sound/music output, each button action, and sensitivity behavior.
- Preload video: cold boot with frame captures at 0.5 s intervals plus controller logs, receipt, `playback-time`, `eof-reached`, and surface z-order.
- GTK theme/browsers/DevMgmt/Software/desktop move: capture exact current behavior and window/viewport metrics before changing anything.

---

# 2. Deep-analysis findings this mission must prove or fix

The companion `DEEP-ANALYSIS.md` contains the full file-and-line analysis. The high-confidence findings are:

1. **Wake ordering is wrong in `nuxel-wl-fb`.** `display_set()` unblanks the panel before a fresh post-wake frame is committed (`tools/s10plus/a67/nuxel-wl-fb.c:1040-1066`). The loop only presents after unblanking (`:1704-1720`, `:1744-1768`). The stale DECON scanout is the primary suspect for the desktop flash.
2. **Home polls display state only every 5 s and hides the lockscreen during display-off.** `app.js:1522-1562`; `style.css:586-606`. A fast off/on sequence can miss the lock transition entirely, and the lockscreen may not be painted when the panel wakes.
3. **Native chrome has a real swipe-direction bug.** Nav dock hides on an upward movement (`nuxel-navdock.c:519-531`); top bar hides on a downward movement (`nuxel-statusbar.c:507-519`). They should hide on the opposite direction.
4. **There are two bottom stripes.** The native nav strip paints a 3 px handle (`nuxel-navdock.c:216-229`) and Home CSS paints a second 4 px pill (`style.css:530-543`). Consolidate to one owner.
5. **Full nav dock is transparent behind the buttons.** `render_frame()` clears the buffer and blits only the three PNGs (`nuxel-navdock.c:204-240`). Paint an opaque full-dock surface while open; keep the collapsed strip transparent.
6. **Timer display is poll-driven and formatted like a stopwatch.** `clock.js:389-458`, `:496-502`; `fmtSw` returns `HH:MM:SS.cc`, and the toast truncates to `00:00`. The Set path is overwritten by the daemon's default idle timer on the next poll. Make the daemon's duration authoritative and paint locally from `deadline_ms`.
7. **Alarm/timer projection appears logically correct but is untrusted.** `clockd._check`, `clockd.status`, `system_indicators.clock_scheduler_state` all look consistent; the reported inversion/missing penguin must be reproduced and fixed at the true source, not by flipping a boolean blindly.
8. **`back()` can leave an invisible ACTIVE app.** The in-app Back path can report `handled` forever, native `/apps/back` can leave stale state, and `gestures.js` refuses the drawer whenever `appSession.state === 'ACTIVE'` even if no visible surface exists (`app.js:1157-1204`, `gestures.js:14`).
9. **Doom always passes `-nomusic`.** `doom.js:503-507`. The UI's SOUND toggle cannot enable music. AudioContext initialization happens after async WAD/engine work and may be suspended. The MENU button pauses the app, not necessarily the engine menu; Use/−/+ key mappings need proof.
10. **Waydroid is unproven and possibly kernel-blocked.** No implementation exists; the live-required kernel config lacks binder/ashmem entries. Do a hard feasibility gate first.
11. **No Services API/UI exists.** Settings has no Services tab; arbitrary `systemctl` from the PWA is unacceptable.
12. **PenguInterface has no spoof controls.** The `spoof/` prototypes are x86_64 and incomplete; build a real aarch64, app-scoped implementation.
13. **Flatpak dark theme is incomplete.** `api.py:3376-3520` writes GTK settings but does not install/force the Flatpak Adwaita-dark theme extension; `flatpak_provider.launch_argv()` has no theme/scale profile.
14. **Browser/Firefox/DevMgmt responsiveness is unverified.** Native browser has a fixed 360×760 default and a rigid toolbar; Firefox has no shipped user.js/policies; DevMgmt tabs need structural CSS hardening.
15. **Preload video likely plays behind WebKit or is released early.** The controller is a correct duration/EOF implementation on paper, but presentation z-order, the 1.2 s map delay, the opaque cover and the 6 s asset must be proven frame-by-frame.

Each workstream below states the exact implementation contract and the proof required. Where a hypothesis may be wrong, instrument and let the live evidence decide; never preserve a false diagnosis just because it is in this document.

---

# 3. Workstream A — zero-flash Power-on to lockscreen

## 3.1 Required end state

Pressing Power to wake a locked phone must show **only** the lockscreen (or the intentional boot animation during a cold boot). There must be zero frames of the desktop, a zoomed/cropped desktop, a stale app, or an unlocked shell. The transition must be deterministic even when:

- the display was blanked by the idle timer,
- the display was blanked by a short Power press,
- the phone was locked manually and then blanked,
- the phone is woken within 5 s of blanking,
- the orientation was changed just before blanking,
- an app was foreground when it locked,
- the preload video/cover is not active (normal wake),
- the user wakes with a touch on the panel instead of Power.

## 3.2 Authority model

Define and enforce exactly one authority per fact:

1. **Panel blank state:** `nuxel-wl-fb` owns `display_on`, `bl_power`, brightness and DECON scanout. It publishes `/run/nuxel-wl-fb.state` and `/var/lib/nuxel/display` atomically.
2. **Session lock state:** the root security provider owns `/run/nuxel/security/lock-state.json`. Every other process is a cache.
3. **Home presentation state:** the Home PWA owns the lockscreen DOM and `body.lockscreen-active` / `body.display-off`, but may only reflect the authoritative security state.
4. **Lockscreen first-frame readiness:** Home must publish a bounded, machine-readable readiness signal after it has painted an opaque lockscreen (wallpaper + lockhead + indicators) at least once.
5. **Wake sequencing:** the bridge/button manager must request wake; `nuxel-wl-fb` must not unblank before Home has an opaque lockscreen frame ready, or must present a cached known-lockscreen frame before unblanking.

Do not let a 5 s polling loop be the authority for a physical Power press.

## 3.3 Implementation contract

### 3.3.1 Event-driven lock and wake

- Add an event-driven path from the button manager / pwa host / bridge to Home for `display-off` and `display-on` transitions. Keep a bounded poll (250–1000 ms) only as a fallback; it must not be the primary path.
- On any physical Power-off, idle timeout, or explicit screen-off, **lock synchronously** in the authoritative state and in Home before or at the same time as blanking. Do not wait for a poll to observe OFF.
- On wake, ask Home to present the lockscreen **before or at the same time as** unblanking. If Home is not ready, unblanking must wait for a bounded readiness gate or present a known-good lock frame.
- If the security provider says locked, Home must show the lockscreen and must never expose `#app-grid`, app surfaces, the dock or the status bar for a single frame.

Suggested state machine:

```text
UNLOCKED/OFF -> [power/idle] -> LOCKED_AND_BLANKING -> PANEL_OFF
PANEL_OFF -> [power/touch wake] -> LOCKED_PAINTING -> LOCKED_PRESENTED -> PANEL_ON
any transitional state -> [failure/timeout] -> LOCKED_PRESENTED (safe fallback)
```

The state transitions must be logged with monotonic timestamps and boot ID.

### 3.3.2 Home CSS/runtime

- Do **not** use `visibility:hidden` on `#lockscreen` while the panel is blanked. The panel is already dark; keep the lockscreen rendered so a wake capture has the correct pixels. Pause expensive animations instead.
- If idle power saving is required, use `content-visibility` carefully or freeze animations, but never remove the lockscreen from compositing in a way that forces a repaint race on wake.
- Keep the lockscreen wallpaper at a stable, measured `cover` geometry. Do not apply a scale transform during wake. If the wallpaper is positioned via measured geometry, compute it from the current `innerWidth/innerHeight` and output scale.
- On `nuxel:display-on`, immediately:
  1. ensure `#lockscreen` is shown and `body.lockscreen-active` is set,
  2. refresh clock/battery/indicators,
  3. force a WebKit/compositor repaint (`host.action('force-redraw')` or the current supported repaint path),
  4. publish a one-shot `lockscreen-presented` readiness marker after two animation frames and an image decode check.
- On `nuxel:display-off`, set the display-off class only for animation/polling suppression; do not hide the lockscreen from the capture tree.

### 3.3.3 `nuxel-wl-fb` wake ordering

Rewrite `display_set(1, ...)` so the sequence is:

1. Record `force_present=1`, `force_full_frames` as needed, and a wake generation counter.
2. Do **not** write `bl_power=0` / backlight until either:
   - a fresh screencopy has been captured and committed to the framebuffer and `FBIOPAN_DISPLAY` has succeeded, or
   - a previously cached known-good lockscreen frame has been re-presented.
3. Capture a fresh composited frame after the wake and compare/commit it. If the capture fails, keep the panel dark and retry within a bounded window; do not expose stale desktop pixels.
4. Only then unblank the panel, restore brightness, assert DECON and publish `DISPLAY_ON` with the wake generation.
5. Present at least one full frame after wake (not a partial damage frame) so a stale band/scale cannot survive.
6. If the panel hardware cannot unblank after a frame commit within the bound, fall back to the safest behavior: unblank dark/black, then present the lockscreen as soon as available, and log the limitation.

Implement the bridge side as an explicit two-phase operation, e.g. internal `wake_prepare()` → `wake_commit()`, not an unblank followed by a later capture. Keep the existing single `/dev/fb0` owner, DECON recovery and damage tracking.

### 3.3.4 Orientation/scale stability

- The wake path must not change output scale/transform. If `nuxel-orientationd` or Phoc changes transform on wake, either hold the last transform until the lockscreen is presented or present the lockscreen at the new transform before unblanking.
- Capture the actual source/output scale in the receipt. A “zoomed” frame is evidence of a scale/transform mismatch; do not dismiss it as a wallpaper crop.
- Verify portrait wake, landscape wake, and a wake immediately after an orientation change.

## 3.4 Tests and evidence

Add tests (unit/static where possible; physical for the actual frame sequence):

- Static contract test: `nuxel-wl-fb` source contains a wake path that does not call `bl_power_write(0)` before the first fresh frame/cached frame commit.
- JS test: no `visibility:hidden` rule hides `#lockscreen` under `body.display-off`; `nuxel:display-on` calls the presentation readiness path.
- State-machine test: OFF→ON within 0 ms/100 ms/1 s/4.9 s all end in `LOCKED_PRESENTED`.
- Physical: 20 wake cycles after idle blank, 20 after Power blank, 5 in landscape, 5 immediately after rotation. Record frame captures; zero desktop frames allowed.
- Bridge evidence: wake generation, capture timestamp, commit timestamp, unblank timestamp, first `FRAMES_OK`, and lockscreen-presented timestamp.

## 3.5 Acceptance

The owner can press Power repeatedly, including quickly after blanking, and never see the desktop or a zoomed desktop for any visible frame. The screen is either black while the panel is off or shows the lockscreen; the transition is bounded and evidence-backed.


---

# 4. Workstream B — Nuxel Doom: sound on by default, working audio, top controls, 3× sensitivity

## 4.1 Required end state

Nuxel Doom must:

- start with sound enabled by default on a fresh profile (and on the owner's existing profile after migration, without destroying their data);
- produce audible sound effects **and** music on the S10+ speaker after the first intentional Play gesture;
- show **no** unconditional `-nomusic` / `-nosound` when the SOUND toggle is on;
- place the **Use**, **−**, **+**, **Map** and **Menu** controls in the top-left and top-right clusters, away from the centered in-game HUD;
- honor a persisted **aim sensitivity** default of exactly 3× the previous turn rate, adjustable and stored;
- make **Use**, **−**, **+**, **Map** and **Menu** each perform their real engine action end-to-end.

## 4.2 Concrete defects to fix

### 4.2.1 Music is unconditionally disabled

`pwa/nuxel-apps/doom/js/doom.js` builds the engine argv with a hard-coded `-nomusic` regardless of settings (`doom.js:503-507`) and adds `-nosound` only when `settings.sound` is false. Remove `-nomusic` from the always-present list; keep `-nosound` for the explicit sound-off case. Do **not** remove `-config default.cfg` or any WAD catalogue arguments.

### 4.2.2 AudioContext starts after an async chain

`callMain(args)` runs after WAD fetch and engine compilation. Create or resume the `AudioContext` (or the WASM SDL audio path) synchronously from the first trusted user gesture on **Play**, before or at engine start, and verify the context state is `running`. If WebKit still blocks autoplay, expose a truthful "tap to enable audio" affordance rather than silently claiming sound while the context is suspended. Never swallow an audio initialization failure: log it and surface it in the Doom HUD.

### 4.2.3 Controls centered over the HUD

`doom.css` centers `−`/`+`/USE/MENU in `.twin-actions` at the bottom and MAP near the top. Re-layout into two top clusters:

- top-left cluster: **Use**, **Map**;
- top-right cluster: **−**, **+**, **Menu**.

Use safe-area insets and avoid covering the engine HUD. Keep the existing walk/aim/fire pads below.

### 4.2.4 Aim sensitivity default ×3

There is no sensitivity setting today; aiming is digital `applyAim`/`aimPulse` pulses. Add a `sensitivity` setting, default `3` (meaning 3× the current pulse rate/duty cycle), persisted in Doom's settings schema, and apply it as a real multiplier on the turn-rate/duty cycle. Prove the change by measuring pulses per second at sensitivity 1 vs 3 on the live device. Do not fake it with a label.

### 4.2.5 Button wiring must actually work

Verify each control end-to-end in a running game:

- **Use** opens a door/switch (`Space`, scan code 32/57);
- **−** / **+** switch weapons (`BracketLeft`/`BracketRight` or the engine's real prev/next scan codes — confirm against the Chocolate Doom 3.0 key table, not assumption);
- **Map** toggles the automap (`KeyM`, scan code 77);
- **Menu** opens the engine pause menu (not just the app-level `pauseEngine` overlay).

Correct any mismatched scan codes. Verify Resume, Return to Launcher, and Exit each cleanly release held keys, restore audio policy, and leave no stranded engine process.

## 4.3 Doom audio tests and evidence

- Fresh-profile launch (cleared test profile): SOUND is on, and a gameplay effect + music are audible after the first Play tap.
- Existing-profile launch: migrate persisted `sound`/new `sensitivity` without data loss; confirm the old `sound:false` is respected but a fresh default is `true`.
- Capture the actual engine argv, `AudioContext.state`, and the output route on the speaker for each run.
- Measure sensitivity: pulses/time at the default vs sensitivity 1, and confirm the persisted value survives close/reopen.
- Verify all five controls perform their real action; record a short on-device proof (audio/frame) with no private data.

---

# 5. Workstream C — Waydroid: hard feasibility gate, then ServiceNow / Microsoft Authenticator / Aegis

## 5.1 Required end state

One of two honest outcomes:

1. **Feasible:** Waydroid runs as the real `nuxel` user on the existing Wayland session, with a launcher entry, and ServiceNow Mobile Agent, Microsoft Authenticator and Aegis Authenticator installed from owner-provided official sources and tested for real behavior.
2. **Blocked:** the exact missing kernel/namespace prerequisites are documented as `BLOCKED_KERNEL` with precise evidence, and no Waydroid package is faked or half-installed.

Do not pretend either outcome.

## 5.2 Feasibility gate (must precede any install)

On the live phone prove or disprove every prerequisite:

```bash
ls -l /dev/binder /dev/binderfs /dev/ashmem 2>/dev/null || true
lsmod | grep -Ei 'binder|ashmem' || true
zcat /proc/config.gz 2>/dev/null | grep -Ei 'BINDER|ASHMEM|PSI|NAMESPACES|CGROUP' || true
unshare -Ur true 2>&1 || true
```

Verify `CONFIG_ANDROID_BINDER_IPC`, `CONFIG_ANDROID_BINDERFS`, `CONFIG_ASHMEM`, `CONFIG_PSI`, user-namespace support, and cgroup availability. The S10+ is a downstream Samsung 4.14 kernel; Flatpak already struggles with unprivileged user namespaces on it, so Waydroid may be blocked by the same gates. Do **not** flash a kernel as part of this userspace round — a kernel change is a separate, explicitly approved safety gate with backup, recovery and a rollback image.

## 5.3 Install path (only if the gate passes)

1. Install the Fedora Waydroid package and official Android images.
2. Run Waydroid as the real `nuxel` user on the existing Phoc/Wayland session; create a launcher entry via the normal app registry.
3. Install the requested Android apps from **owner-provided official APKs or official stores only**. Never enable unknown repositories, and never log credentials or capture MFA seeds.
4. Test touch, keyboard, network, audio, rotation, lock/unlock, and the triple-button/top-bar chrome over the Waydroid window; verify recovery and clean teardown.

## 5.4 Honest app-by-app test matrix

| App | Expected behavior | Realistic risk | Required evidence |
|---|---|---|---|
| Aegis Authenticator | Should work without GMS; import/export local vault only, no cloud login | Low | screenshot-free proof of install/launch and a dummy local entry (no real seed) |
| Microsoft Authenticator | Likely needs GAPPS / Play Integrity / push | High — may refuse or warn | exact refusal/warning text and Android/Play version reported; no credentials |
| ServiceNow Mobile Agent | Depends on Android WebView/Play services and network | Medium | exact launch/network behavior; no instance credentials |

Report what actually happens — including refusal, missing WebView, missing GMS, rotation errors — rather than "installed successfully" from a package manager exit code.

---

# 6. Workstream D — Triple buttons & top bar: opaque chrome, one stripe, correct gestures, space reclamation

## 6.1 Required end state

Across Nuxel Home, GTK+ apps (Archive Manager), Electron/Flatpak messenger apps (Signal/Telegram/Legcord/Caprine), Firefox, and PWAs:

- **Nav (bottom triple buttons):** swipe **up** reveals, swipe **down** hides.
- **Top bar:** swipe **down** reveals, swipe **up** hides.
- While the full nav dock is open, nothing behind the buttons is visible — the dock paints an opaque surface behind the three buttons.
- When the nav dock or top bar collapses, the freed space is reoccupied by the app and its hit-testing; when it expands, the app content does not bleed through and the band is reserved.
- Exactly **one** bottom swipe affordance is visible at a time (no native strip + CSS pill simultaneously).
- Gestures work in messenger apps specifically, where the current strip band is too small / clashing.

## 6.2 Concrete fixes

### 6.2.1 Correct the native swipe-direction bugs

- `tools/s10plus/a45/nuxel-navdock.c:519-531` hides the full dock on an **upward** movement; it must hide on a **downward** movement. Reveal remains upward.
- `tools/s10plus/a45/nuxel-statusbar.c:507-519` hides the full bar on a **downward** movement; it must hide on an **upward** movement. Reveal remains downward.

Preserve the existing layer-shell exclusive-zone logic (full 62 px nav / 36 px top; strip 0) and verify the compositor clients actually resize/grow when the zone returns to 0.

### 6.2.2 One bottom stripe owner

The native `nuxel-navdock` paints a 3 px translucent handle (`nuxel-navdock.c:216-229`), while Home CSS paints a second 4 px pill (`pwa/nuxel-home/css/style.css:530-543`). Choose **one** owner. Recommended: when the native dock overlay is present, remove the Home CSS pseudo-strip; keep the native handle as the single affordance. Add a regression test that asserts no two-stripe combination can render.

### 6.2.3 Opaque full-dock surface

`nuxel-navdock` `render_frame()` clears the buffer transparent and blits only the three PNGs (`nuxel-navdock.c:204-240`), so app content shows between/behind the buttons. Paint a fully opaque Nuxel mat behind the buttons while the full dock is open (and keep the collapsed strip transparent). The top bar already paints an opaque strip when full — keep that behavior.

### 6.2.4 Larger input band without stealing app taps

The strips are 14 px (nav) and 12 px (top). A finger starting a few pixels inside the app cannot be seen by the strip surface, which is why messenger-app gestures fail. Increase the **input** region to a comfortable 32–40 logical px at the very edge while keeping the visual handle thin. Do not use global input injection, and do not swallow normal app content taps outside the edge band.

### 6.2.5 Space reclamation and iframe geometry

- For native apps, the full→strip exclusive-zone change must cause the app surface to reoccupy the freed band; verify with the compositor's actual usable-area change.
- For the PWA/DOM chrome, when `body.app-status-revealed` or the DOM nav bar is revealed, the iframe top/height must follow the actual revealed state; when hidden, the app is full height. Verify no ghost band remains that blocks app touch.

## 6.3 Tests and evidence

- One affordance per edge; capture screenshots at 0%/50%/100% gesture.
- Direction matrix on Home, Archive Manager, one Electron/Flatpak messenger, Firefox, one PWA.
- Full chrome opaque (no app glyphs through the button row); collapsed chrome reoccupies space and reaches the edge.
- Two-stripe regression test passes.
- Record touch start/end coordinates and whether each gesture succeeded in each app.

---

# 7. Workstream E — Timer: smooth countdown, sub-minute values, no duplicate penguin, heavy shake

## 7.1 Required end state

- The timer counts down smoothly and visibly every second with no irregular jumps, "sluggish" pauses, or stale snapshots.
- Timers shorter than one minute (e.g. 30 s, 5 s) display and run correctly — never `0:00` before expiry.
- Exactly **one** timer penguin exists per active timer; no second penguin appears above the original when it goes off.
- The timer penguin shakes **heavily** when the timer fires.

## 7.2 Root causes to fix

### 7.2.1 Sluggish display

`pwa/nuxel-apps/clock/js/clock.js` calls `tick()` every 500 ms (`clock.js:501`) but `paintTimer()` repaints from the last scheduler snapshot, refreshed by a bridge RPC every 1000 ms (`clock.js:496-502`). Replace the poll-driven display with a local, deadline-driven paint loop (`requestAnimationFrame` or a 250 ms monotonic loop) that computes remaining time from `deadline_ms`/`remaining_ms` locally and reconciles with the daemon at a lower cadence (1–2 s). The daemon remains the authoritative scheduler; the app is only a view.

### 7.2.2 Sub-minute timers become `0:00`

`fmtSw()` returns `HH:MM:SS.cc` (`clock.js:65`), and the Set toast truncates to `HH:MM` with `.slice(0, 5)` (`clock.js:417`), so a 30 s timer shows `0:00` in the toast and `00:00:30.00` in the main time. Also, Set injects a local object, but the next 1 s scheduler poll overwrites it with the daemon default `duration_ms`/`remaining_ms` (300000). Fix:

1. Format timers as `MM:SS` (or `H:MM:SS` only when ≥ 1 h), with a real sub-minute form.
2. Make `reset-timer`/`set-timer`/`start-timer` authoritative in `nuxel-clockd` (the daemon stores the requested duration), not a transient local object that the next poll clobbers.
3. Ensure the Set action persists the chosen duration and the UI never displays the daemon's 5-minute default for a requested 30 s.

### 7.2.3 Duplicate timer penguin on expiry

Instrument DOM node count, scheduler occurrences by `run_id`/`id`, and rendered rectangles before changing layout. Dedupe by `run_id`; ensure exactly one projection is rendered during the `completed → ringing` transition (`nuxel-clockd._check()` sets `completed` then creates a ringing occurrence, and `stop-timer` marks ringing occurrences dismissed while setting timer to `acknowledged`). Never render both "completed" and "ringing" states simultaneously. Enforce a hard invariant: **one timer lane → one penguin → one active run**.

### 7.2.4 Heavy shake

The current shake is ±7° / ±5 px (`lockscreen.css:551-607`) and is masked by the lane scale transition. Introduce a heavier, clearly visible shake (e.g. ±18–24° rotation with a small positional jitter, repeated) animated on the **inner image** or a dedicated wrapper, so it cannot conflict with the lane positioning transform or the drag transform. Keep `prefers-reduced-motion` handling if present.

## 7.3 Tests and evidence

- Set 5:00, 0:30, 0:05; record displayed values each second for 5 s; no `0:00` for sub-minute before expiry; smooth cadence.
- Trigger expiry; assert exactly one timer penguin node and one visible penguin rectangle across the full `running→completed→ringing→acknowledged` transition.
- Heavy shake is visible on device (short video/frame sequence).
- Persistence: a 30 s timer survives Clock close/reopen and continues to run in the daemon.

---

# 8. Workstream F — Lockscreen penguin placement (timer + alarm over wallpaper)

## 8.1 Required end state

- The **timer** penguin sits at the horizontal center of the screen, vertically **on top of** the wallpaper penguin.
- The **alarm** penguin sits at the horizontal center, vertically **below the wallpaper penguin** (and thus below the timer placement) and **above the lock/unlock penguin**.
- Both shake heavily when their respective event fires (see Workstream E/G).
- Layout is measured, not hardcoded, and survives orientation changes.

## 8.2 Implementation contract

- Reuse the wallpaper geometry already measured by `lockscreen.js` (`_coverCssY` and the wallpaper constants) instead of the current right-anchored `top:24%` vertical stack (`css/lockscreen.css:529-539`).
- Position the lanes relative to the computed wallpaper-penguin bounds: timer centered at the wallpaper penguin's center; alarm below it and above the lock/unlock handle, using CSS anchors or measured constraints with safe-area insets.
- Keep the two lanes separate from the unlock handle hit target; both indicator gestures and the unlock gesture must coexist without accidental activation.
- Do not hardcode pixel coordinates for one viewport; compute from measured logical viewport/safe areas.

## 8.3 Tests and evidence

- Screenshot/framebuffer capture at portrait and landscape with both indicators visible; verify centered horizontal alignment and correct vertical ordering (timer over wallpaper penguin; alarm between wallpaper penguin and lock handle).
- Rotate while indicators are visible; layout re-measures without overlap or drift.

---

# 9. Workstream G — Alarm: on/off inversion, enabled-visible penguin, heavy shake

## 9.1 Required end state

- Alarms fire **only** when enabled. The On/Off semantics are correct (On = enabled = will fire).
- An enabled alarm shows its lockscreen penguin **while enabled** (before it rings), not only while ringing.
- A disabled alarm shows no penguin and never fires.
- The alarm penguin shakes heavily when the alarm fires.

## 9.2 Root-cause discipline

The backend projection `system_indicators.py:1137-1179` computes `alarm_visible` from *any enabled alarm*, which appears logically correct; and `clock.js:316-321` sends `enabled: !a.enabled` when toggling, which is also logically correct. The reported inversion/missing penguin must therefore be reproduced end-to-end and fixed at the true source — likely a stale `clockd.state`, legacy `sync` overwrites, or a localStorage alarm-list cache rendering while the daemon says otherwise. Do **not** blindly flip the boolean again; that would merely invert the bug.

Required instrumentation:

- Trace a full create → disable → enable → edit → delete → fire cycle against `nuxel-clockd.state` and the client cache at every step.
- Determine which source (daemon vs localStorage) the UI is actually rendering from and reconcile them to a single authority (the daemon).
- Add explicit state-transition tests: disabled alarm never fires; enabled one-shot and recurring fire; enabled future occurrence shows penguin immediately; fired one-shot with no future occurrence does not leave a stale penguin.

## 9.3 Heavy shake

Apply the same heavy-shake contract as Workstream E to the alarm penguin, on a dedicated wrapper, isolated from the drag-follow transform.

## 9.4 Tests and evidence

- Create disabled alarm → no penguin, no fire. Enable → penguin appears immediately; alarm fires at due time. Disable → penguin disappears, alarm does not fire.
- One-shot vs weekly recurrence with seven weekday checkboxes persist across Clock close/reopen and reboot.
- Fired alarm shakes heavily and sound plays (see 87000 round); right-dismiss removes only that occurrence; left-snooze preserves future occurrences.
- Verify `alarm_visible` in the daemon projection matches the rendered penguin at all times.

---

# 10. Workstream H — Foreground visibility truth: invisible app must not block the drawer

## 10.1 Required end state

When an app quits (Back at root, native window closed, or otherwise) but remains invisible while the session still considers it foreground, the Applications drawer **must still open**. Holding Back to force-kill must not be the only recovery path.

## 10.2 Fix direction

- Maintain a **foreground visibility truth** independent of the `ACTIVE` string: for PWAs, frame connected, not `hidden`, computed `display` not `none`, non-zero rect intersecting the viewport, and document not `hidden`; for native apps, an active real `foreign-toplevel` window exists.
- `gestures.js:14` currently refuses the drawer whenever `appSession.state === 'ACTIVE'` even if no visible surface exists. Change it to refuse only when a **visible** foreground surface exists.
- Add a bounded watchdog (1–2 s) while state is `ACTIVE`: if no visible surface is found, background the app and show Home. Never silently keep an invisible foreground.
- Make `back()` idempotent/bounded (`app.js:1157-1204`): if an in-app Back reports handled but the surface remains invisible/unchanged, background/close after a bounded retry; always allow a subsequent Home/drawer gesture.
- `_backgroundForegroundApp()` must clear the foreground surface and reset chrome/status so Home is genuinely foreground again.

## 10.3 Tests and evidence

- PWA at root Back returns to Home and opens drawer.
- PWA with a history handler that lies (`NuxelBack` always handled) still yields a backgrounded/closed surface within the watchdog bound.
- Native window closed externally → `appSession` reconciles; drawer opens.
- Hidden iframe due to lifecycle → watchdog recovers.
- Long-Back force-kill still works, but is no longer required.

---


---

# 11. Workstream I — Settings → Services: safe systemd control with unlock gate

## 11.1 Required end state

Settings has a new **Services** tab offering enable/disable/start/stop/reload/restart plus `systemd daemon-reload` and `daemon-reexec`, protected by an explicit unlock button. Every service that is **system-essential** (can break core functionality when stopped) is marked as such, and its stop/disable is blocked in the GUI; restart/reload additionally require confirmation.

## 11.2 Architecture constraints

- The bridge runs as root; the new service-control endpoint must be **allowlisted**, must not accept arbitrary unit names from the client, and must never execute client-supplied commands directly.
- Read-only inventory + explicit unlock gate. The unlock must be a server-side token/acknowledgement, not merely a disabled HTML button.
- Essential flags must live in a **shipped policy file**, not be hardcoded in JS.
- Verify results with `systemctl is-active` / `is-enabled`; write an audit log; expose no secrets.

## 11.3 Essential-service policy (minimum set)

Mark at least these as system-essential (stop/disable blocked in GUI; restart/reload confirmed): `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-button-manager`, `nuxel-touch-arm`, `nuxel-bridge`, `nuxel-http-bridge`, `nuxel-web`, `nuxel-soundd`, `nuxel-clockd`, `nuxel-orientationd`, `nuxel-device-permissions`, `nuxel-audio-route`, `nuxel-audio-session`, `seatd`, and the USB/Wi-Fi restore units. Reconcile against the actual live unit list (Workstream 1.2) and extend as needed.

## 11.4 Safety semantics

- `daemon-reload` and `daemon-reexec` are the highest risk; add an extra confirmation hold and a countdown, and only perform them after `systemctl is-system-running` / failed-unit inspection.
- Never stop/disable/re-exec essential services without the safety procedure in this document.
- `restart`/`reload` of an essential service must be explicitly confirmed and must preserve the lock state, Wi-Fi SSH reachability and recovery.
- Log every action to the audit trail with timestamp, actor, unit, verb, before/after state.

## 11.5 Tests and evidence

- List services, see active/enabled state and essential markers.
- Unlock gate required before any mutating action.
- Stop/disable of an essential service is refused with a clear message.
- Start/stop/reload/restart of a non-essential service works and `is-active`/`is-enabled` reflects the change.
- `daemon-reload` and `daemon-reexec` succeed and the system remains healthy; Wi-Fi SSH stays reachable.

---

# 12. Workstream J — PenguInterface: user-agent / os-release / uname / LD_PRELOAD spoofing + reset

## 12.1 Required end state

PenguInterface gains a real spoof panel able to:

- show the current user agent;
- edit/spoof the user agent (per-app where applicable);
- spoof `/etc/os-release`;
- spoof `uname` output;
- use `LD_PRELOAD` for app-scoped spoofing (modeled on `./spoof`);
- **reset** everything with one button that removes all spoofs and verifies the underlying system is unchanged.

## 12.2 Source facts

`pwa/nuxel-apps/penguinterface` is currently a read-only device-compatibility profile viewer (`js/pengu.js`, `profile.json`). The `spoof/` directory contains the owner's Fedora-laptop prototypes: `fake_uname.c`, `fake_os.c`, `fake_windows.c`, `fake_os.js`, `teams-spoofer.js`, plus prebuilt **x86_64** `.so` files that are not usable on the aarch64 phone. The prototype `fake_os.c` `open()` wrapper mishandles varargs and lacks `openat`/`open64`/`fopen64`/`stat` coverage.

## 12.3 Implementation contract

1. **PenguInterface spoof panel:** current UA, UA editor, os-release fields, uname fields, target-app selector, apply/off/reset.
2. **aarch64 library:** build a separately named `libnuxel-spoof.so` with correct symbol interposition and recursion-safe `dlsym`/`dlopen`; generate `/run/nuxel/spoof/os-release` and a profile JSON. Fix the varargs/coverage defects from the prototype; cover `uname`, `open`/`openat`/`open64`/`fopen64`/`stat`/`statx`/`readlink` for the os-release redirect as needed.
3. **Scope:** apply `LD_PRELOAD` only to explicitly selected app launches by default; never to system services, the bridge, Phoc, `nuxel-wl-fb`, root shells, or unrelated services. System-wide spoofing requires an explicit warning/unlock and is out of scope unless the owner insists.
4. **User agent:** per-app WebKit setting for Nuxel Browser/PWA host; Chromium/Electron `--user-agent`; Firefox profile/policy. Verify the target app actually sees the spoofed UA.
5. **Reset:** removes the profile, environment injection and config; restarts affected apps; verifies native `uname`/`os-release` outside the spoof are unchanged.
6. Never store credentials, and document anti-cheat/ToS and app-breakage risk.

## 12.4 Tests and evidence

- Show current UA matches the bridge/reported value.
- Apply a UA spoof to the Nuxel Browser and verify the browser reports the spoofed UA.
- Apply os-release + uname spoof to a test GTK/CLI app; confirm it sees the fake values while a separate process outside the spoof sees the real values.
- Reset removes all spoofs; `uname -a` and `cat /etc/os-release` on the device are unchanged; affected apps restart cleanly.
- No system service, root shell, Phoc or bridge process has `LD_PRELOAD` injected.

---

# 13. Workstream K — Adwaita-dark GTK/Flatpak, responsive browsers, DevMgmt tabs

## 13.1 Adwaita-dark for GTK+ and Flatpak apps

Archive Manager, Firefox, and other GTK/Flatpak apps still render light. `api.py:3376-3520` writes GTK settings but never injects `GTK_THEME` per process and never installs the Flatpak Adwaita-dark theme extension; `flatpak_provider.launch_argv()` (`:1016-1056`) has no dark-theme/scale/UA environment.

Fix:

1. Ensure `org.gtk.Gtk3theme.Adwaita-dark` (and the GTK4 equivalent if used) is installed and present in the Flatpak remotes.
2. Set `GTK_THEME=Adwaita:dark` (or the correct theme name) and `GTK_APPLICATION_PREFER_DARK_THEME=1` for native and Flatpak GTK launches.
3. Persist dark `color-scheme` in GTK 3 and 4 settings and `~/.config/gtk-3.0/settings.ini`/`gtk-4.0/settings.ini`.
4. Verify Archive Manager and Firefox (native + Flatpak where applicable) render dark.

## 13.2 Responsive Nuxel Browser and Firefox

- `shell/nuxel-browser-native/nuxel_browser_native.py` hardcodes `set_default_size(360,760)`, no maximize/fullscreen, no mobile UA override, fixed horizontal toolbar. Make it maximize to the actual viewport, set an appropriate mobile/default UA, allow toolbar wrap/overflow, and verify `window.innerWidth`, `devicePixelRatio`, and touch scrolling on the S10+.
- Firefox has no shipped `user.js`/`policies.json`. Ship a documented profile/policy setting device pixel ratio/scale, dark system theme, compact UI, and responsive behavior. Verify actual viewport metrics and touch scroll.
- Both must be measured on-device, not asserted from config files.

## 13.3 DevMgmt tabs

`.tabs` already has `overflow-x:auto; scrollbar-width:none;` and hidden WebKit scrollbars (`devmgmt.css:15-18`), but text overlaps at DPI/font scale. Add `flex-shrink:0` on tab buttons, explicit line-height/padding, `min-width:0` on the parent, `scroll-padding`, and `scrollIntoView({inline:'center'})` on the active tab. Verify at narrow widths and long labels; tabs scroll horizontally without a visible scrollbar.

## 13.4 Tests and evidence

- Screenshots: Archive Manager and Firefox dark; no light mode.
- Nuxel Browser and Firefox fill the viewport, respond to touch scroll, and report sane `innerWidth`/`devicePixelRatio`.
- DevMgmt tabs never overlap text and scroll without a scrollbar; active tab visible.

---

# 14. Workstream L — Software app: future apps work instantly and responsively

## 14.1 Required end state

Any app installed via the Software app works immediately — visible to the launcher, launchable, responsive — without per-app flags or manual investigation. Same for RPM and Flatpak installs.

## 14.2 Fix direction

- Add a **post-install integration hook** that, after a Flatpak/RPM install, refreshes the Flatpak app list and desktop entries, updates the launcher app registry, and creates a generic launch profile (toolkit, WM class, scale, theme, UA, focus/maximize policy).
- `flatpak_provider` caches Electron/QtWebEngine detection per app id; new installs are cold. Make detection metadata-based and persist the result so new apps get a profile immediately.
- For unknown toolkits, use `flatpak run` + generic Wayland/software fallback, then focus/maximize and verify a real surface exists.
- `nuxel-software` currently launches only installed Flatpaks (`:482-510`); RPM installs are not followed by a launcher refresh. Add both.
- Apply generic display scale/theme/UA from the measured output scale, not per-app flags.

## 14.3 Tests and evidence

- Install a representative Flatpak and an RPM app; both appear in the launcher and launch instantly with correct focus and responsive sizing, no flags.
- Verify the generic profile persists across reboot.
- Verify the install does not require the owner to investigate or edit flags.

---

# 15. Workstream M — Desktop drag + Move/Desktop-N action row for apps and widgets

## 15.1 Required end state

- Desktop application icons can be dragged to another free grid cell, and the position persists.
- Long-pressing an app icon shows an action row with **Resize**, **Remove**, **Move**, **Desktop N**, **Done** — replacing **Home settings** (not adding a sixth item).
- **Move** arms a real drag/grid-picker and persists the snapped cell.
- **Desktop N** shows the current desktop number; tapping it opens a desktop picker (Desktop 1, 2, … up to the configured count) and moves the app there to a free cell.
- Widgets get the **same** action row and Move/Desktop-N behavior.

## 15.2 Fix direction

- `launcher.js` already has drag state, ghost, grid hit-testing, edge dwell, `desktopLayout.move()` and persisted layout (`:879-1100`); long-press at `:771-776` enters edit mode and auto-starts drag, which makes the action-row interaction fragile. Disentangle long-press from auto-drag so the action row is stable, and Move arms an explicit drag.
- `_renderEditToolbar()` (`:1116-1129`) currently renders `Resize`, `Remove`, `Home settings`, `Done`. Replace with `Resize`, `Remove`, `Move`, `Desktop N`, `Done`.
- `widgets.js` has resize/remove and its own long-press drag (`:207-227`, `:318-421`) but no widget action bar or Move/Desktop N. Add the equivalent action row; child controls inside a widget must still work.
- All changes must go through the shared `desktop-layout.js`/`layout-model.js` occupancy model; no second collision map, no duplicate entities after a move.

## 15.3 Tests and evidence

- Long-press app → action row shows Move and Desktop N; Move drags to a free cell and snaps; persisted across reload/reboot.
- Desktop N picker moves app to Desktop 2 (and back); occupancy/collision resolved predictably.
- Widget action row offers Move/Resize/Remove/Desktop N/Done; child controls still work.
- No duplicate entity/identity after cross-desktop move.

---

# 16. Workstream N — Performance smoothing and boot-time reduction (measured)

## 16.1 Required end state

Nuxel is measurably smoother, and boot time is reduced, with evidence for every change. Revert any change that does not improve the measured target or adds risk.

## 16.2 Measurement first

Capture before/after:

```bash
systemd-analyze time; systemd-analyze blame | head -40; systemd-analyze critical-chain | head -60
cat /run/nuxel-wl-fb.state
ps -eo user,pid,ppid,comm,%cpu,rss,args --sort=-%cpu | head -60
```

Record idle wakeups, WebKit/Phoc load, app launch times, and frame timings.

## 16.3 Safe candidate changes (prove each)

- Preserve `nuxel-wl-fb` as sole fb owner with damage tracking, static-frame skipping, idle capture pacing and display-off sleep.
- `nuxel-preload-cinema` hashes the full 7.6 MB asset on every boot (`:866-889`) and runs a 4 s launcher wait + 1.2 s map delay; cache the hash and remove serial delays that are not required for correctness.
- `nuxel-session.sh` may run a 10 s HTTP fallback wait; `NetworkManager-wait-online` and optional services serialize boot. Reduce/parallelize where safe without breaking Wi-Fi SSH return.
- Audit Home/clock/status/lockscreen polling loops (1 s, 5 s, 10 s, 0.5 s) and make them event-driven where possible.
- Do **not** add a GPU/DRM path the kernel does not support; do not regress boot, recovery, Wi-Fi SSH, touch, Phoc/Wayland, framebuffer ownership, Mali/EGL, audio, orientation, camera, storage, or Flatpak.

## 16.4 Evidence

Before/after `systemd-analyze` numbers, frame timings, CPU/RSS, idle wakeups, and app launch times. Report which changes were kept and why.

---

# 17. Workstream O — Preloading video: full 6-second playback and clean handoff

## 17.1 Required end state

`assets/nuxel-preloading-screen.mp4` plays its full ~6.0 s clip (H.264 1080×1920, 24 fps, 144 frames, 6.016 s), with advancing frames the whole time, topmost on screen, then hands off to a rendered lockscreen. No early cut, freeze, static poster, or hidden playback.

## 17.2 Likely root cause

The controller is a correct duration/EOF implementation on paper, but presentation z-order, the 1.2 s map delay, the opaque Home cover, and the 6 s asset must be proven frame-by-frame (`services/nuxel-preload-cinema/nuxel-preload-cinema:612-644`, `:887-1169`). The clip may be playing behind WebKit or being released early, so the owner only sees the visible tail or a poster.

Fix:

1. Prove topmost surface ownership for the `mpv` `wlshm` window through the whole clip; raise it above WebKit/Home until the clip ends.
2. Remove or bound the 1.2 s map delay and any 4 s launcher wait that are not required for correctness.
3. Confirm EOF is actually reached before release, or use a bounded grace period with a truthful fallback to the lockscreen.
4. Ensure the Home `#preload-cover` is removed only after the controller reports terminal, and that the lockscreen is already painted.
5. If the asset has an audio track, keep audio policy off (it is a silent boot clip); do not introduce sound.

## 17.3 Tests and evidence

- Cold boot with frame captures every 0.5 s plus controller logs, receipt, `playback-time`, `eof-reached`, and surface z-order.
- Verify ≥ 6.0 s of advancing `playback-time` and changing frames, topmost, then clean handoff to lockscreen.
- Force missing asset, decoder failure, player crash, and readiness timeout in a test environment; every failure reveals a safe lockscreen within bounded time.

---

# 18. Workstream P — Other deep-analysis findings and safety gates

Re-run the full deep-analysis flow on the live device and repair any **additional** real defects found, without turning this into an uncontrolled rewrite. Prioritize:

- any remaining wake/lock race beyond Workstream A;
- any second framebuffer writer, second scheduler, second dock/top bar, or second preload controller;
- stale caches/localStorage overriding authoritative daemon state (clock, layout, spoof, settings);
- Flatpak/Electron/QtWebEngine launch-profile coldness for already-installed apps;
- any leftover light-mode GTK/Flatpak apps;
- any remaining invisible-foreground or drawer-block path;
- boot-critical services with broad `After`/`Wants` chains that serialize unnecessarily.

Every additional fix must be documented with root cause, test, and physical or explicit-blocker evidence.

---

---

# 19. Deployment, backup, rollback, evidence and report

## 19.1 Deployment discipline

- Stage to a temporary path, verify SHA-256, atomically install, set owner/mode, restart only the affected unit, and verify state. Never overwrite newer live work with an older ZIP, backup, or prompt version.
- Deploy repository-side and on-device components consistently; confirm remote hashes match the intended files and service reloads are confirmed before claiming deployment.
- Root may own system daemons and the bridge. GUI/WebKit apps, PipeWire clients, and user data run in the real `nuxel` session context.

## 19.2 Backups and rollback

- Create a timestamped full backup of every file, unit, config, service state and active data that will be migrated or overwritten.
- Produce a hash manifest, tested rollback commands, and (where a reboot is required) a recovery-access confirmation.
- Do not reboot unless required and only after confirming backup integrity and Wi-Fi SSH expected return.

## 19.3 Evidence

Write evidence beneath:

```text
docs/pwnage-88000/evidence/<UTC_TIMESTAMP>/
```

Include before/after hashes, command transcripts, unit status, journal excerpts, event/cue receipts, test results, frame/audio verification, screenshots/framebuffer captures with no private data, and rollback commands.

## 19.4 Automated tests

Run the focused existing suites and add regression tests for every repaired contract. Validate syntax, lint, cache/version updates. New tests must cover at minimum:

- wake ordering / no `bl_power_write(0)` before first frame commit; OFF→ON state machine;
- timer formatting (sub-minute never `0:00`), local deadline paint, exactly one timer penguin;
- alarm enable/disable/fire/penguin projection state transitions;
- foreground-visibility truth and drawer access;
- single bottom stripe / opaque full-dock / swipe-direction contracts;
- Doom argv (no unconditional `-nomusic`), sensitivity multiplier, control scan codes;
- services allowlist and essential-policy refusal;
- spoof scoping and reset;
- desktop/widget move + Desktop-N persistence.

## 19.5 Final engineering report

Finish with `docs/pwnage-88000/evidence/<timestamp>/ENGINEERING-REPORT.md` summarizing root causes, files changed, services restarted, what was actually heard/seen/touched on hardware, automated tests, regressions checked, known limitations, and precise rollback instructions. Then give the owner a concise result summary.

## 19.6 Final acceptance

A workstream passes only when its acceptance tests pass on the actual S10+ (or is explicitly marked not physically verifiable with the exact blocker). Do not declare success based on code presence, an HTTP 200, a CSS class, or a label. Prove the physical outcome.

**Execute the complete `full-pwnage-88000.md` now.**
