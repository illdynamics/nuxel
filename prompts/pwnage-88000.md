# PWNAGE-88000 — Operation Zero-Flash, Heard Doom, Real Services & Living Spoof

**Kickstarter / execution prompt**  
**Authoritative full specification:** `full-pwnage-88000.md` (read it completely before changing anything)  
**Companion analysis:** `docs/pwnage-88000/DEEP-ANALYSIS.md`  
**Target:** Nuxel on Samsung Galaxy S10+ (`SM-G975F`, `beyond2lte`, Exynos 9820, ARM64)  
**Primary transport:** Wi-Fi SSH to the running Nuxel root console  
**SSH key:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Mission:** eliminate the wake desktop flash, fix Doom audio/controls/sensitivity, gate and (if possible) install Waydroid + the three Android apps, repair triple-button/top-bar chrome and gestures, correct the timer/alarm penguins and scheduling, restore foreground/drawer reliability, add a guarded Services section, build real PenguInterface spoofing, force dark GTK/Flatpak, make browsers/DevMgmt/Software responsive and future-proof, finish desktop/widget Move + Desktop-N, smooth performance and boot, and restore the full preloading video.

---

## Mission command

Read **all of `full-pwnage-88000.md`** before changing anything. Treat it as the implementation specification. Work in the current Nuxel repository and on the actual S10+ over Wi-Fi SSH. Inspect the live phone first: the checkout is on `pwnage-80000` with many uncommitted changes, and the phone may be newer than the repository. Live state and deployed hashes win; never overwrite newer work with older files from a ZIP or an earlier prompt.

This is an implementation and verification task, not another planning exercise. Diagnose each failure, fix it end-to-end, deploy narrowly with backups, and verify on the physical handset. The owner explicitly asked for every line in the full spec; treat each as a required outcome.

## Mandatory Wi-Fi root connection

From `~/x/nuxel`, use the project's Wi-Fi helper and the existing key:

```bash
cd ~/x/nuxel
KEY=~wicked/.ssh/wicked_wqn_id_rsa
test -r "$KEY" || { echo "OWNER SSH KEY MISSING"; exit 1; }
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --status --user root --key "$KEY"
```

Discover/revalidate the current phone WLAN address (historical values such as `192.168.178.167` are hints only). Open the root console:

```bash
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_WLAN_HOST" \
  --user root --key "$KEY" --shell
```

Confirm `id -u` is `0`, then capture the baseline dossier from `full-pwnage-88000.md` section 1. Do not use `StrictHostKeyChecking=no`, host-key deletion, or private-key disclosure, and do not silently fall back to USB/serial. If Wi-Fi SSH is unavailable, document the exact failure and continue with safe repository-side work only; do not claim physical verification.

## Priority workstreams (see the full spec for the exact contract)

1. **Zero-flash Power-on → lockscreen** (A, also item 18): fix `nuxel-wl-fb` wake ordering so the panel is never unblanked before a fresh/cached lockscreen frame is committed; make Home lock event-driven, keep the lockscreen renderable while the panel is off, and prove zero desktop frames across idle-blank, power-blank, rapid off/on, rotation, and touch-wake.
2. **Doom** (B): remove unconditional `-nomusic`, start with sound on by default, produce real effects + music after the first Play tap, move Use/Map to top-left and −/+/Menu to top-right, add a persisted 3× aim-sensitivity multiplier, and prove all five buttons work in-game.
3. **Waydroid** (C): run the hard feasibility gate first (binder/ashmem/PSI/namespaces). If blocked, report `BLOCKED_KERNEL` with exact missing prerequisites and prepare a separate kernel plan — do not flash a kernel here. If feasible, install Waydroid and test ServiceNow Mobile Agent, Microsoft Authenticator, and Aegis from official owner sources with an honest app-by-app matrix.
4. **Triple buttons / top bar** (D): fix the native swipe-direction bugs, consolidate to one bottom stripe, paint an opaque full-dock surface, enlarge the edge input band for messenger apps, and prove space reclamation on collapse.
5. **Timer** (E): local deadline-driven smooth countdown, correct sub-minute formatting (no `0:00`), exactly one timer penguin on expiry, and heavy shake when it fires.
6. **Lockscreen penguin layout** (F): timer penguin centered over the wallpaper penguin; alarm penguin centered below it and above the lock/unlock penguin; measured, not hardcoded.
7. **Alarm correctness** (G): alarms fire only when enabled; enabled alarm shows its penguin while enabled (before ringing), not only while ringing; heavy shake on fire. Do not blindly re-flip the boolean — find the real daemon-vs-cache authority bug.
8. **Foreground visibility truth** (H): an invisible app must never block the Applications drawer; make Back bounded/idempotent and add a 1–2 s watchdog so long-Back force-kill is not the only recovery.
9. **Services section** (I): add a guarded Settings→Services tab with start/stop/restart/reload/enable/disable, `daemon-reload`, `daemon-reexec`, an unlock gate, and an essential-services policy that blocks stopping/breaking core units.
10. **PenguInterface spoofing** (J): current UA, UA spoof, os-release spoof, uname spoof, app-scoped `LD_PRELOAD` built as aarch64 `libnuxel-spoof.so`, and a one-button reset that proves the underlying system is unchanged.
11. **Dark GTK/Flatpak + browsers + DevMgmt** (K): force Adwaita-dark for Archive Manager/Firefox and others, make Nuxel Browser and Firefox responsive, and fix DevMgmt tab overlap with scrollable tabs and no scrollbar.
12. **Software post-install profiles** (L): future Flatpak/RPM installs work instantly and responsively with a generic launch profile — no per-app flags or investigation.
13. **Desktop/widget Move + Desktop-N** (M): app icons draggable on the grid; action row becomes Resize/Remove/Move/Desktop N/Done (replace Home settings); widgets get the same row and behavior.
14. **Performance & boot** (N): measured smoothing and boot-time reduction; revert anything that does not improve the measured target.
15. **Preloading video** (O): play the full ~6.0 s clip topmost with advancing frames, then clean handoff to the lockscreen.
16. **Anything else** (P): re-run the full deep-analysis flow and fix any other real defects found, without an uncontrolled rewrite.

## Non-negotiable engineering rules

- Inspect `git status`, diffs, source versions, current deployed hashes, services, journals and the phone's runtime before editing. Live state wins.
- One owner per concern: one framebuffer writer (`nuxel-wl-fb`), one scheduler (`nuxel-clockd`), one sound owner (`nuxel-soundd`), one dock, one top bar, one preload controller, one desktop-layout model.
- Do not fake Waydroid, spoofing, audio, service control, app launch, gesture input, frame playback, or hardware state. Do not substitute mocks, test tones, static labels, or screenshot-only checks for real operation.
- Do not add a second `/dev/fb0` writer. Do not stop/disable/restart/re-exec essential services without the full spec's safety procedure.
- Do not apply `LD_PRELOAD`, spoofed `/etc/os-release`, or spoofed `uname` to the bridge, Phoc, `nuxel-wl-fb`, systemd, root shells, or unrelated services. Scope spoofs to selected app launches.
- Do not flash kernel, boot, recovery, super, userdata, or repartition anything for these userspace defects. A kernel change for Waydroid is a separate, explicitly approved gate.
- Do not store credentials, MFA seeds, session cookies, tokens, or private keys in source, logs, command arguments, evidence, or screenshots. Do not install random APKs or enable unknown repositories.
- Preserve boot, recovery, Wi-Fi SSH, touchscreen, Phoc/Wayland, framebuffer ownership, Mali/EGL, audio routing, MFC, orientation, camera, storage, and Flatpak sandboxing.
- Root may own system daemons and the bridge; GUI/WebKit apps, PipeWire clients, and user data run in the real `nuxel` session context.

## Required verification (summary)

- 20+ wake cycles after idle blank, 20 after Power blank, 5 landscape, 5 after rotation: zero desktop frames.
- Doom fresh + migrated profile: sound on, real effects + music, five controls working, 3× sensitivity measured and persisted.
- Waydroid: either running with the three apps honestly tested, or `BLOCKED_KERNEL` with exact prerequisites.
- Triple buttons/top bar: correct reveal/hide directions in Home, Archive Manager, one Electron messenger, Firefox, and a PWA; one stripe; opaque open dock; space reclaimed on collapse.
- Timer: smooth sub-minute countdown, one penguin, heavy shake. Alarm: enable/disable correct, enabled penguin visible before ringing, heavy shake.
- Invisible-foreground recovery: drawer opens without long-Back.
- Services: guarded tab, essential units protected, actions verified with `is-active`/`is-enabled`, `daemon-reload`/`daemon-reexec` safe.
- Spoofing: UA/os-release/uname/LD_PRELOAD apply to selected apps and reset cleanly with the system unchanged.
- Dark GTK/Flatpak, responsive browsers, DevMgmt tabs scroll without overlap.
- Software installs work instantly; desktop/widget Move + Desktop-N persist.
- Boot time and smoothness measured before/after; preload video plays full 6 s topmost.

## Tests, deployment and report

Run the focused existing test suites and add regression tests for every repaired contract (see full spec section 19.4). Validate syntax, lint, and cache/version updates. Deploy with a timestamped full backup, hash manifest, atomic writes, narrow restarts, and tested rollback. Reboot only if required and only after confirming recovery access and backup integrity.

Write evidence beneath `docs/pwnage-88000/evidence/<UTC_TIMESTAMP>/`, including before/after hashes, transcripts, unit status, journal excerpts, receipts, test results, frame/audio verification, and screenshots with no private data.

Finish with `docs/pwnage-88000/evidence/<timestamp>/ENGINEERING-REPORT.md` summarizing root causes, files changed, services restarted, what was actually heard/seen/touched on hardware, automated tests, regressions checked, known limitations, and precise rollback instructions. Then give the owner a concise result summary.

**Execute the complete `full-pwnage-88000.md` now.**
