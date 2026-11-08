# PWNAGE-87000 — Operation Alarm Penguin & Buttersmooth Boot

**Kickstarter / execution prompt**  
**Authoritative full specification:** `full-pwnage-87000.md`  
**Target:** Nuxel on Samsung Galaxy S10+ (`SM-G975F`, `beyond2lte`, Exynos 9820, ARM64)  
**Primary transport:** Wi-Fi SSH to the running Nuxel root console  
**SSH key:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Mission:** repair the Clock alarm/timer audio and lockscreen interaction, restore Doom audio and menu usability, make desktop icon/widget move mode reliable, and repair the two-stage Nuxel boot/preloading animation.

---

## Mission command

Read **all of `full-pwnage-87000.md` before changing anything**. Treat it as the implementation specification. Work in the current Nuxel repository and on the actual S10+ over Wi-Fi SSH. Inspect the current live phone state first: the supplied repository snapshot predates the 84000 deployment, and the live phone now has `nuxel-clockd`, `nuxel-soundd`, and later uncommitted/deployed work. Do not overwrite newer work with older files from the ZIP or blindly replay earlier implementation prompts.

This is an implementation and verification task, not another planning exercise. Diagnose each failure, fix it end-to-end, deploy narrowly with backups, and verify on the physical handset.

## Mandatory Wi-Fi root connection

From `~/x/nuxel`, use the project's Wi-Fi helper and the existing key:

```bash
cd ~/x/nuxel
KEY=~wicked/.ssh/wicked_wqn_id_rsa
test -r "$KEY"
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --status --user root --key "$KEY"
```

Use the helper's current discovered/reachable Wi-Fi host. The last successful session used `192.168.178.167`; an older pinned helper host `10.20.30.16` was stale at that time. Revalidate the host on this run and preserve normal SSH host-key checking. Open the shell through the helper:

```bash
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_WLAN_HOST" \
  --user root --key "$KEY" --shell
```

Confirm `id -u` is `0`. Do not use USB/serial as a silent fallback, `StrictHostKeyChecking=no`, host-key deletion, or private-key disclosure. If Wi-Fi SSH is unavailable, document the exact failure and continue with safe repository-side work; do not claim physical verification.

## Priority workstreams

1. **Clock alarm/timer sound:** the lockscreen penguins already shake and their gestures work, but neither alarm nor timer is audible. Trace the real event path from `nuxel-clockd` through `nuxel-soundd`/`nuxel-soundctl`, PipeWire/ALSA and the S10+ speaker. Fix the actual failure. Verify sound while locked and with the display off. Keep alarm and timer sound selections separate.
2. **Lockscreen penguin layout and gestures:** put the timer penguin directly over the central wallpaper penguin. Put the alarm penguin bottom-centre, below the wallpaper penguin and above the lock/unlock slider. During an alarm swipe, the penguin artwork must visibly follow the finger just as the unlock handle does. Right dismisses only the current alarm occurrence; left snoozes it. Timer penguin tap stops that timer and its sound. Unlock must continue to work when both indicators are visible. Hide the alarm penguin if no enabled alarm has a future occurrence; show it for enabled upcoming one-shot or recurring alarms. Alarm editor must support enabled/disabled, once, and weekly recurrence with seven independent weekday checkboxes.
3. **Doom audio and menu:** inspect `pwa/nuxel-apps/doom/js/doom.js`. The supplied source defaults `sound: true` but passes `-nomusic` unconditionally in its Chocolate Doom arguments. Correct the sound policy so the default starts with working sound effects and music, subject to the engine's real capabilities and WebKit audio-unlock requirements. Test on the speaker. Verify the in-game MENU/Pause button opens the pause menu, Resume works, Return to Launcher works, and Exit works without stranded keys or audio. Do not silently swallow audio initialization failures.
4. **Desktop move mode:** holding an application icon must offer the same action bar as its existing resize/delete mode, with a working **Move** action. Move mode must support drag-to-position and grid snapping. Holding a widget must open the equivalent widget action bar and support move, resize and remove. Do not break the existing edge-drag desktop transfer or desktop ownership model. Ensure all controls work with actual touchscreen pointer events, not only synthetic tests.
5. **Boot/preloading media:** diagnose why `assets/nuxel-preloading-screen.mp4` fails or becomes a stuck static frame. Repair its real Wayland `mpv` presentation path and readiness/EOF handoff. During the Wayland-starting/loading interval, use the existing spinning-penguin `assets/nuxel-boot-animation.mp4` (or its already-generated framebuffer-native NUX animation artifact where that is the correct stage) as a looping temporary animation instead of a frozen frame from the preloading-screen clip. Preserve the original assets and the one-writer framebuffer design. Never let the old cinema overlay conceal the real lockscreen indefinitely.

## Non-negotiable engineering rules

- Inspect `git status`, diffs, source versions, current deployed hashes, services, journals and the phone's actual runtime before editing. The 84000 deployment report is newer than the supplied ZIP; live state wins.
- For alarm/timer audio, test a known-good speaker playback first, then trace the exact cue. Do not call an API success merely because a request returned HTTP 200 or a daemon accepted a message. Verify audible PCM/output on the physical speaker and capture relevant status/journal receipts.
- Do not use browser-page `Audio()` as the system alarm owner. Clock is a client; `nuxel-clockd` owns scheduling and `nuxel-soundd` owns sound delivery. Do not duplicate schedulers.
- Keep occurrence state separate from alarm definitions. Snoozing or dismissing one occurrence must not damage other future alarms or a recurring schedule.
- Never make lockscreen indicators authoritative from stale localStorage. Query the clock daemon's real persisted schedule/active ringing state.
- Keep lockscreen alarm and timer gesture ownership isolated from the unlock handle. Use pointer capture, real-time transform following, correct `pointerup`/`pointercancel` handling, and prevent gesture bubbling only for the gesture that began on that icon.
- Do not hardcode layout coordinates for one viewport. Measure the real logical viewport/safe areas and use CSS anchors or measured layout constraints.
- Do not remove Doom's essential controls. Sound is on by default; settings must persist. Do not disable effects just to hide an audio error.
- Do not create another framebuffer writer. `nuxel-wl-fb` remains the sole `/dev/fb0` writer during the Wayland session. The early `nuxel-anim-player` and Wayland `mpv` presentation belong to different boot stages; hand off explicitly.
- Preserve source MP4 hashes, orientation, aspect ratio, audio policy and color characteristics. Validate with `ffprobe`, actual decode and on-device playback.
- Preserve boot reliability, TWRP recovery, Wi-Fi SSH, touchscreen input, Phoc/Wayland, framebuffer ownership, Mali/EGL, audio routing, MFC, orientation and Flatpak sandboxing. No broad kernel/bootloader/partition flash for these userspace issues. Any necessary boot-image change requires a separate proven delivery plan, backup and explicit safety gate.
- Do not store passwords, tokens, session cookies, SSH key contents or MFA codes in source, logs, command arguments, test fixtures or evidence.
- Do not substitute mocks, test tones, static success labels or screenshot-only checks for real operation.

## Required verification

### Clock / lockscreen

- Create a one-shot alarm and a weekly alarm; verify enable/disable and all seven weekday checkboxes persist across Clock close/reopen and reboot.
- Disable every alarm: no alarm penguin. Enable a future alarm: alarm penguin appears. Delete all alarms: it disappears. A fired one-shot with no remaining future occurrence must not leave a stale indicator.
- Trigger a real alarm on speaker with the screen on and locked, then locked with display off. Confirm sound is audible, the alarm icon shakes, follows the finger horizontally, right dismisses only this occurrence, left snoozes for the configured interval, and upcoming/recurring alarms remain intact.
- Trigger a real timer. Confirm it sounds, its penguin shakes, one tap stops the sound and hides the timer indicator, without dismissing alarms.
- Drag alarm and unlock handles in both orders while both indicators are visible. No overlapping hit target, accidental dismissal, accidental unlock or stuck pointer capture.
- Exercise separate alarm and timer sounds, changing each independently.

### Doom

- Clear no user data; inspect current persisted Doom settings and migrate them safely if schema changes.
- Fresh launch has sound enabled. Verify an actual gameplay sound effect and music are audible on the S10+ speaker after the first intentional Play gesture. Confirm no unconditional `-nomusic` remains when sound is enabled.
- Verify the MENU/Pause HUD button opens the pause screen; Resume returns to gameplay; Return to Launcher returns cleanly to the Doom start screen; Exit returns to Nuxel Home. No held keys, leaked audio or stuck immersive mode.

### Desktop move mode

- Long-press an app icon and explicitly select Move from the action bar. Drag to a different free grid cell; release; verify snapped position persists after reload/reboot.
- Long-press a widget. Its own action bar offers Move, Resize, Remove and supported desktop transfer. Drag to another free cell, resize, remove and recreate. Do not move an app when the widget is held or vice versa.
- Test edge-drag transfer between desktops with the object still held, then drop; verify collisions are rejected or resolved predictably.

### Boot animation

- Cold boot and record stage-by-stage timestamps. The early framebuffer animation, Wayland-starting loop, Wayland preloading clip and final lockscreen must have explicit owners and clean handoffs.
- Verify the Wayland-loading period displays moving frames from the spinning-penguin asset, not one static poster frame. Verify the preloading-screen clip advances through frames to EOF (or its configured bounded end), then reveals the real lockscreen.
- Force missing asset, decoder failure, player crash and readiness timeout in a test environment. Every failure must reveal a safe live lockscreen/fallback within its bounded timeout.
- Prove there is no framebuffer writer race, black-screen hang, permanent overlay, duplicate controller or late overlay over an unlocked desktop.

## Tests, deployment and report

Run the focused existing test suites and add regression tests for every repaired contract. Validate syntax, lint and cache/version updates. Deploy with a timestamped full backup of all files, units, configs, service state and active data that will be migrated. Use atomic writes and narrow service restarts. Reboot only if required and only after confirming recovery access and backup integrity.

Write evidence beneath:

```text
docs/pwnage-87000/evidence/<UTC_TIMESTAMP>/
```

Include before/after hashes, command transcripts, unit status, relevant journal excerpts, event/cue receipts, test results, frame/animation verification, screenshots or framebuffer captures with no private data, and rollback commands.

**Do not declare success based on code presence.** A workstream passes only when its acceptance tests pass on the actual S10+ or is explicitly marked not physically verifiable with the exact blocker.

Finish with `docs/pwnage-87000/evidence/<timestamp>/ENGINEERING-REPORT.md` summarizing root causes, files changed, services restarted, what was actually heard/seen/touched on hardware, automated tests, regressions checked, known limitations and precise rollback instructions. Then give the owner a concise result summary.

**Execute the complete `full-pwnage-87000.md` now.**
