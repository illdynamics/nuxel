# FULL-PWNAGE-87000 — Operation Alarm Penguin & Buttersmooth Boot

## Complete source-led implementation specification for Nuxel on the Galaxy S10+

**Target device:** Samsung Galaxy S10+ `SM-G975F`, codename `beyond2lte`, Exynos 9820, ARM64  
**OS:** Nuxel / Fedora ARM64 mobile Linux  
**Known kernel baseline from the latest reported live session:** Linux `4.14.253-gf7194c1d15ed-dirty` (re-discover; do not assume unchanged)  
**Primary access:** Wi-Fi SSH to the Nuxel root console using `~wicked/.ssh/wicked_wqn_id_rsa`  
**Repository:** `~/x/nuxel`  
**Round:** PWNAGE-87000  
**Mission:** restore audible system alarms and timers, refine their lockscreen interaction, restore Doom audio/menu behavior, finish app/widget move-mode interactions, and repair the Wayland preloading/boot animation handoff.

---

# 0. Mission command and definition of done

Execute every workstream in this document. This is not a request for a mockup, a speculative diagnosis, or a new plan that leaves the repository unchanged. Inspect the source and the actual running S10+ first, find the root cause of each reported failure, implement the fix across the necessary service/UI/packaging layers, deploy safely, and prove it on the physical phone.

The current state is newer than the supplied `nuxel-main (12).zip` source snapshot. The latest user-provided 84000 execution report records a successful Wi-Fi root session, a live `nuxel-clockd`, `nuxel-soundd`, PipeWire 1.4.11, deployed PWA and bridge changes, and 37/37 automated tests passing. That report is useful historical evidence, not a substitute for inspecting current live state. The ZIP snapshot includes older versions of Clock/Doom/lockscreen code. **Do not overwrite newer live/repository changes with stale ZIP versions.** Reconcile current `git status`, the current checkout, deployed hashes, and the running phone before editing.

## 0.1 Required outcomes

1. Alarm and timer notifications must be audible through the S10+ speaker when the phone is locked and when the display is off, subject to demonstrated hardware power/wake capability. Fix the sound path rather than the visual animation.
2. Timer and alarm penguins must occupy the requested lockscreen positions, the alarm penguin must visibly follow the user's finger during horizontal swipe, the timer penguin must stop the timer on one tap, and the existing unlock gesture must still work without overlap or accidental activation.
3. Alarm configuration must support enable/disable, one-time alarms, weekly recurrence with seven independent weekday choices, persistence, editing and deletion. The alarm indicator must represent actual future enabled alarms and disappear when none remain.
4. Doom must launch with sound enabled by default and produce audible sound effects and music. Its menu/pause controls must function end-to-end.
5. App icons and widgets must reliably enter the same recognizable move/edit interaction model. The app action bar needs a real Move action; widgets need the equivalent action bar and real drag support.
6. The Wayland startup/loading interval must show a moving loop of the spinning-penguin `nuxel-boot-animation` rather than a frozen frame from `nuxel-preloading-screen.mp4`. The preloading screen itself must play correctly as a moving clip and hand off to the real lockscreen.
7. All work must preserve the existing boot/display/input/audio architecture and be backed by reproducible tests, evidence and rollback instructions.

## 0.2 Mandatory Wi-Fi SSH access

The owner explicitly requires Wi-Fi SSH and the existing key. Use the project helper first:

```bash
cd ~/x/nuxel
KEY=~wicked/.ssh/wicked_wqn_id_rsa
test -r "$KEY"
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --status --user root --key "$KEY"
```

Discover the phone's current WLAN address. The last successful session used `192.168.178.167`; the older helper-pinned address `10.20.30.16` was reported stale/unreachable. Treat those only as historical hints, never as facts about the current network. Use the helper's verified host/known-hosts configuration. Open the root console:

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
```

No `StrictHostKeyChecking=no`, no host-key deletion, no key-content printing, no switching to USB/serial without explicitly reporting that Wi-Fi access failed. Do not alter the phone until host authenticity, root privileges, and current boot mode are confirmed. If connection fails, collect the exact diagnostic and continue only with repository-side work; mark all physical checks unverified.

## 0.3 Execution principles

- Be evidence-driven. Reproduce every symptom before patching it.
- Preserve every already-working system: Nuxel boot, `nuxel-wl-fb`, Phoc/Wayland, Mali/EGL, touch routing, audio playback, Bluetooth, Wi-Fi, orientation, MFC, Camera work, Flatpak sandboxing, launcher and filesystem data.
- Avoid gratuitous architecture rewrites. Reuse the currently deployed `nuxel-clockd` / `nuxel-soundd` contracts and current launcher/widget infrastructure where sound; repair missing or broken links.
- No fake success. A daemon accepting a message does not prove the speaker emitted sound. A test asserting a CSS class does not prove the phone's finger interaction works. A media file existing does not prove frames are moving on screen.
- Root may own system daemons and the bridge. GUI/WebKit applications, PipeWire client operations and all user data must run in the actual logged-in Nuxel session context, not as root.
- Do not expose private secrets, key contents, browser data or credentials in logs or evidence. Do not add credentials or tokens to any source/config file.
- Persistent changes need a timestamped backup, atomic deployment and rollback. Avoid unnecessary reboots; if one is required, confirm the device can be recovered and Wi-Fi SSH is expected to return.
- Keep the source tree, live phone and generated evidence consistent. Do not call a deployment successful until remote hashes match the intended files and service reloads are confirmed.

---

# 1. Repository and live-device reconnaissance

## 1.1 Establish the real current code state

Before edits:

```bash
cd ~/x/nuxel
git status --short --branch
git log -5 --oneline --decorate
find docs -maxdepth 3 -type f \( -iname '*pwnage*report*' -o -iname 'ENGINEERING-REPORT.md' \) | sort | tail -80
```

Locate and read the latest PWNAGE-84000 / 85000 / 86000 engineering reports if present. The latest 84000 report states that the source work was partly uncommitted at deployment time and that physical verification of some lockscreen gestures was pending. Capture any follow-up report or uncommitted change set created after that report. Do not discard or reset working-tree changes.

Inspect the current versions of at least:

- Clock PWA and its service/API client.
- `nuxel-clockd` source, unit, state schema, IPC/API contract and migration code.
- `nuxel-soundd`, `nuxel-soundctl`, its unit, cue registry, event handlers and PipeWire/ALSA backend.
- Bridge endpoints and the lockscreen scheduler status provider.
- Lock-screen HTML, CSS, `lockscreen.js`, `lockscreen-indicators.js`, tests and service-worker cache manifest.
- Doom `index.html`, `doom.js`, `doom.css`, WebAssembly/SDL build metadata, default config and tests.
- Launcher app-item long-press/action-menu/move/resize/delete implementation, widget implementation, grid model and multi-desktop persistence.
- Preload cinema controller, systemd/session launch path, mpv args/IPC, Wayland startup stage markers, initramfs boot animation player and asset packaging.

Use `git diff`, current deployed hash comparisons, and direct source inspection. The older ZIP's Clock JS says alarms only run while Clock is open; the live 84000 deployment report says a persistent `nuxel-clockd` was added. That difference is intentional and must not be reversed. Likewise, the ZIP lockscreen indicator controller predates the alarm/timer integration and may not match the running system.

## 1.2 Capture the live baseline

Record, without exposing secrets:

- `uname -a`, `/etc/os-release`, boot ID, uptime, device model and rootfs identity.
- Current display geometry/orientation, `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-pwa-host`, session and lockscreen processes.
- `systemctl --no-pager --full status` for clockd, soundd, bridge, session, Wayland, framebuffer bridge and preload-cinema units; `systemctl cat` each relevant unit.
- `journalctl -b` excerpts for clockd/soundd/PipeWire/preload-cinema/Wayland/session, filtered by event timestamps and request IDs.
- The true session user's UID, GID, home, DBus session bus, PipeWire runtime socket and application environment. Do not infer a session from the SSH user's environment.
- Active audio cards, profiles, sinks, source routes, volume, mute state, ALSA controls, PipeWire nodes and route-selection policy.
- Current schedule data: number of alarms, enabled count, upcoming occurrence, current ringing occurrence and timer state. Redact labels if they contain private information.
- Doom app shell/cache hashes, currently selected engine, settings schema and actual runtime command arguments.
- Current launcher and widget grid state, desktop count, grid geometry and the status of long-press/move handlers.
- `mpv` version, preload-cinema unit/controller arguments, config, asset paths/hashes, IPC status, receipts and logs. Inspect initramfs animation source/build artifacts separately.

Write a baseline JSON/text dossier beneath `docs/pwnage-87000/evidence/<UTC_TIMESTAMP>/baseline/`.

## 1.3 Prove current services and paths

Do not guess paths such as `/usr/libexec/nuxel/nuxel-clockd`; discover them from:

```bash
systemctl show -p ExecStart,FragmentPath,User,Group,Environment nuxel-clockd.service
systemctl cat nuxel-clockd.service
systemctl show -p ExecStart,FragmentPath,User,Group,Environment nuxel-soundd.service
systemctl cat nuxel-soundd.service
ps -eo user,pid,ppid,comm,args | grep -E 'nuxel-(clockd|soundd|bridge|wayland|wl-fb)|pipewire|wireplumber|mpv' | grep -v grep
```

Use the current documented service names if they differ. Use `readlink -f /proc/<pid>/exe`, `/proc/<pid>/environ` with secret-safe filtering, and `systemctl show` to verify what is actually running. Avoid printing access tokens or arbitrary environment variables to the evidence report.

---

# 2. Clock: restore audible alarm and timer operation

## 2.1 Scope and known state

The latest 84000 report says:

- A persistent `nuxel-clockd` scheduler was deployed and enabled.
- A persistent `nuxel-soundd` central sound manager exists.
- PipeWire 1.4.11 was running on the S10+.
- The audio system exposed `S10+ speaker (RDMA1)` and `S10+ microphone (WDMA1)`.
- An alarm E2E test reached `FIRED`, then a `clock-alarm-…` token, then `soundd last_cue_action=alarm`, with a reported ~19.68 ms cue response.
- A timer E2E test fired and acknowledged `stop-timer`.
- On the owner's current handset, the penguins visibly shake and the gesture UI works, but **no audible sound is heard when the alarm or timer fires**.

The mismatch between daemon acknowledgement and no audible sound is the primary defect. Trace the full chain and identify where audible frames disappear. Do not assume it is a UI problem, or that an acknowledged sound cue means playback happened.

## 2.2 Trace the full sound path

Map this chain with request IDs/timestamps at every boundary:

```text
clockd schedule/occurrence
  -> event dispatch (alarm-fired / timer-expired)
  -> soundd request (alarm or timer cue)
  -> selected sound preference / resolved asset
  -> user/session audio context (if used)
  -> PipeWire node / ALSA PCM / Samsung audio route
  -> actual S10+ speaker transducer
```

For each boundary, capture:

- Request and event ID, occurrence ID and timestamp.
- Which daemon sent the request and under which UID/GID.
- Cue type (`alarm` vs `timer`), resolved asset ID/path and checksum.
- Playback backend chosen; PipeWire connection/socket and target sink.
- Whether the playback process/client was created, started, wrote frames, reached EOF, stopped, or received an error.
- Actual target sink, mute state, volume and route availability.
- Whether the screen was locked/display-off and whether the audio route/power state changed.

Use the real `nuxel-soundctl` and `nuxel-soundd` interface after inspecting `--help`, source and status API. Do not assume an invented command syntax. Test a known-good installed sound asset through the same route and prove audibility. Compare a normal notification cue, a manual alarm cue, a manual timer cue, and the scheduled event path.

Likely root-cause categories to examine (test, do not assume):

1. `clockd` emits a legacy action name while soundd only registers a new cue name, or timer and alarm cue names map incorrectly.
2. soundd accepts a cue but uses a stale asset path, nonexistent selected sound, invalid URL, or wrong user's home path.
3. soundd runs as root or a system unit without the graphical user's PipeWire/DBus environment and therefore cannot reach the real session sink.
4. soundd plays into an inactive/null/virtual sink or an unavailable profile instead of the S10+ speaker.
5. The cue is started and immediately stopped by occurrence cleanup, a duplicate stop command, service restart, focus/lock lifecycle event, or sound policy.
6. A service-level sound setting, global mute, per-cue preference or 0-volume value silences the sound.
7. The backend uses a short nonblocking subprocess and reaps/closes its pipe before PCM is drained, or calls `pw-play`/`paplay`/`aplay` with incorrect flags/device.
8. On display-off the device suspends or powers down the audio path; the scheduler fires but lacks the necessary wake/hold mechanism or audio route reactivation.
9. PipeWire/WirePlumber policy changes after lock or screen-off, so a sink disappears or moves.
10. A new sound preference schema is not migrated from the prior `~/Sounds` / user selection store.

The code must distinguish **accepted**, **started**, **audibly streaming**, **completed**, **stopped**, and **failed**. Do not report playback success solely because a cue request was accepted.

## 2.3 Implement a reliable soundd cue contract

Reuse the current sound daemon, do not create another independent alarm/timer player. The sound manager should expose a durable/observable cue state such as:

- `queued`
- `starting`
- `playing`
- `completed`
- `stopped`
- `failed` with a concrete failure code/message

Each event uses a unique `playback_id` and occurrence ID. Starting a timer cue must not silently replace an alarm cue unless an explicit audio-priority policy says it should. A repeated trigger for the same occurrence must be idempotent. The stop command must accept the relevant playback/occurrence ID so stopping a timer never stops an alarm or vice versa.

Requirements:

- Alarm cue and timer cue resolve to separate persisted user preferences.
- Keep default Nuxel alarm/timer assets available as fallback. Verify exact files exist and are decodable; don't make up a filename.
- Resolve all user-owned selections relative to the real Nuxel session user's approved sound directories (`~/Sounds` and approved Nuxel sound library), not `/root`.
- Validate custom sound paths against approved roots; no arbitrary privileged filesystem path playback.
- Handle missing file, unsupported codec, zero-byte file, permission error, sink missing, PipeWire unavailable, and route switch. Present a real failure state and retain a known-good fallback where appropriate.
- The sound client must hold the audio stream until the sound ends or the matching stop request arrives. Avoid daemon process exit closing the stream prematurely.
- Keep the alarm audible at a safe but clearly audible default. Respect global volume and independent user sound settings. If there is an explicit alarm-volume policy, make it visible and persistent; do not silently force maximum volume or bypass user mute.
- Sound preference selection survives app close, daemon restart and reboot.
- Make route activation deterministic when the phone is locked. Do not run GUI apps as root to gain access to PipeWire.

If the current architecture is a system daemon plus a session user sound agent, keep it and repair its IPC. If it is a per-user service, ensure it is activated early enough and survives app closure. Explain the chosen architecture and why it is safe.

## 2.4 Display-off and suspend behavior

The owner specifically expects the alarm/timer to make sound with the phone locked and display off. Test at least these states independently:

1. Clock closed, display on, lockscreen visible.
2. Clock closed, display on, device locked.
3. Device locked, display blanked/off while CPU/session continues.
4. Device in actual system suspend/deep sleep, if the current kernel/device policy allows it.

Do not conflate “display off” with “CPU suspended.” Use wakeup-source, RTC wakealarm, service logs, `/sys/power/state`, wakeup-source state and actual event timestamps to determine what the handset does. If a scheduler must wake the CPU from suspend, inspect the current RTC and wakealarm capabilities first. Implement an RTC/wakeup mechanism only if this hardware/driver exposes it and a safe supported path exists. A systemd inhibitor or suspend blocker must be scoped to the next pending alarm, released promptly, visible to power management and battery-conscious. Do not simply disable all suspend or hold a wake lock forever.

For a display-off alarm, ensure the sound route is opened/activated correctly without requiring the user to unlock or open Clock. If the sound path needs a short route-warmup, perform it in a bounded, non-audible way or as part of the event pipeline; do not produce random test beeps. Log whether the audio route was ready and how it was activated.

## 2.5 Alarm configuration model

Implement and document a versioned alarm schema. At minimum each alarm definition must contain:

```json
{
  "id": "stable-id",
  "label": "Work",
  "time": "07:30",
  "enabled": true,
  "schedule": {
    "kind": "once | weekly",
    "date": "YYYY-MM-DD",
    "days_of_week": [1, 2, 3, 4, 5]
  },
  "sound_id": "optional-per-alarm-selection",
  "volume": "optional-policy-defined-value",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

Adjust names to existing project conventions, but do not collapse one-time and weekly alarm semantics into an ambiguous boolean. `days_of_week` must have a documented mapping (e.g. Monday=1 through Sunday=7). A weekly alarm with no selected weekdays is invalid and must not be saved/enabled. A one-time alarm needs a real date and must not be silently interpreted as “tomorrow” after it has expired.

### UI behavior

- Every alarm row has a clear enabled/disabled toggle that works immediately and persists.
- Provide Add and Edit flows; users can change label, time, once/weekly type, date where needed, weekday checkboxes, sound selection and any supported alarm preferences.
- Weekly UI shows seven independent checkboxes labelled Mon–Sun. One tap on “all weekdays” may be offered, but all seven days must remain individually selectable; selecting all seven means a weekly daily recurrence.
- Once alarms must be scheduled for an explicit date (default may be today only when the selected time is still in the future; otherwise use the next logical date or ask the UI to select it explicitly—never silently schedule in the past).
- Keep existing alarm data. Migrate the prior `repeat: true` daily boolean to a weekly schedule with all seven days, and `repeat: false` to an appropriate once schedule using the best-known original date. Where date cannot be reconstructed safely, flag it for user review rather than deleting or silently changing it.
- Sorting and next-occurrence display use the user's local timezone. Account for DST jumps/repeats and timezone changes; store intent as local wall-clock schedule plus timezone policy, and compute next occurrence safely.
- Toggling or deleting one alarm must not alter other alarms, snooze state, or timer state.

## 2.6 Occurrence state, snooze and dismissal

Separate an alarm definition from an alarm occurrence. Each firing has a unique occurrence ID and lifecycle:

```text
scheduled -> due -> ringing -> snoozed -> ringing -> dismissed
                                      \-> dismissed
```

The actual code may model snooze as its own scheduled occurrence, but preserve the same semantics.

- **Right swipe:** dismiss only the currently ringing occurrence. Stop only its playback ID. Do not delete, disable or dismiss other alarms. A recurring definition remains enabled and its next occurrence remains scheduled. A completed one-shot definition may be disabled/marked completed after the occurrence has been dismissed; preserve a user-visible history if the app already has one.
- **Left swipe:** snooze only the currently ringing occurrence for the configured number of minutes. Keep the recurring/one-shot definition intact and schedule the snooze occurrence independently. At the snooze deadline, it must genuinely fire again, play the alarm cue again and shake the icon again.
- A second upcoming alarm must not be lost if it becomes due while a previous alarm is ringing/snoozed. Handle concurrent due occurrences deterministically: queue or present them in an explicit ordered manner; never overwrite one occurrence with another.
- Restart or reboot during ringing/snooze must not lose the occurrence. Use persisted state and idempotency to avoid double fire.
- Snooze length remains configurable; use a sensible default of 9 minutes if the current user preference does not exist. A disabled snooze setting removes or disables the left-swipe action and makes the UI honest about the absence of snooze. Do not hard-code 5 minutes in one UI handler while the service uses 9.
- Dismissal is per occurrence, not “stop all alarms.” Timer stop is separate from alarm dismissal.

## 2.7 Alarm indicator truth rules

The alarm penguin appears if and only if one of the following is true:

- There is at least one currently ringing alarm occurrence; or
- There is at least one enabled alarm definition whose next real occurrence is in the future (including a valid recurring weekly schedule); or
- There is a valid pending snooze occurrence.

An alarm definition that exists but is disabled must not show the indicator. A one-shot alarm in the past that has been completed must not show it. Deleting all alarms and having no ringing/snoozed occurrence must remove the indicator without requiring a reboot. If all saved “Work” alarms are configured but switched off, no alarm penguin is visible.

Timer indicator visibility is independent. A running timer or expired/ringing timer shows the timer penguin; a stopped/acknowledged timer does not. Clearing timer state must not hide or stop an upcoming alarm.

Expose a truthful clock/scheduler status snapshot over an existing authenticated local bridge/API. It should include a monotonically increasing revision or update timestamp so the lockscreen can refresh reliably. Do not use `localStorage` as the authoritative lockscreen state.

---

# 3. Lockscreen: layout, touch ownership and live animation

## 3.1 Requested positions

The two Clock penguins must be distinct, visually clear, and never cover the original lock/unlock control:

1. **Timer penguin:** centered on the horizontal centerline of the phone and aligned directly over the penguin artwork in the lockscreen wallpaper. Use measured wallpaper image geometry and the real logical viewport. It should appear visually attached to/over the wallpaper penguin, not at the current status-indicator row.
2. **Alarm penguin:** centered horizontally, below the background penguin and above the lock/unlock slider/handle. Maintain a visible gap from both the central timer icon and the unlock handle. Do not put it over the lockhead's active drag hit target.
3. Other status indicators (charging, PC, live console, USB/WLAN/file-transfer/Bluetooth) retain their existing meaning and their own region. Do not merge Clock indicators into unrelated transport/power status classes or overwrite those fields.

Use a layout container with explicit stacking, z-index and safe-area rules. Determine actual `innerWidth`, `innerHeight`, device scale, current orientation, CSS pixels, and alpha-painted bounds. The device is normally portrait, but do not break landscape diagnostics. Use CSS variables or measured anchors rather than absolute coordinates guessed from a 760 px viewport.

## 3.2 Alarm penguin must follow the finger

The owner specifically reports that the alarm swipe works but the penguin does not visibly drag along with the unlock icon. Implement the same visual feedback quality as the lockscreen unlock handle:

- On pointerdown inside the alarm penguin, begin an alarm-specific gesture object with pointer ID, origin, last position, start timestamp, current translateX and threshold state.
- Call `setPointerCapture` on the alarm interaction element where supported; also use a safe window-level fallback, matching the proven lockscreen handle pattern.
- Move the visible image with the finger on every pointermove using a compositor-friendly `transform: translate3d(...)`. Do not move only the invisible wrapper while the PNG stays visually fixed.
- Clamp movement to a safe horizontal range. The icon should visibly travel in both directions without crossing into timer/lock controls.
- Do not apply a transition while actively dragging; restore a short spring/snap transition only after release/cancel.
- On release beyond threshold, dispatch right-dismiss or left-snooze exactly once for that occurrence. Keep the icon in its ringing animation/state until the service acknowledges the action, then animate to rest/remove it based on authoritative state.
- On an incomplete/vertical/cancelled drag, return the penguin to center smoothly. Do not trigger snooze/dismiss for a simple tap or accidental touch.
- Handle `pointerup`, `pointercancel`, `lostpointercapture`, orientation change, visibility change, lock/unlock and service response timeout without leaving the icon offset or an input lock behind.
- Do not use `touchmove` and pointer events simultaneously in a way that fires the action twice. Respect `touch-action: none` only on the actual gesture element.
- Set accessible labels and live state. The image itself remains non-draggable as a browser asset; the parent is the interactive button/gesture surface.

## 3.3 Timer tap behavior

- The timer penguin has a generous touch target but does not overlap the alarm swipe region.
- A single tap requests `clock.stop-timer` / current authoritative API with the active timer occurrence ID.
- Stop its sound playback ID only; do not stop or silence an alarm.
- Hide the timer penguin after acknowledgement and refreshed authoritative state. If the stop fails, retain visible state and show a truthful failure/retry indication; do not pretend it stopped.
- Do not interpret a horizontal swipe on the timer icon as alarm snooze or dismissal.

## 3.4 Unlock remains independent

Existing unlock uses its own pointer-driven state machine and a draggable `nuxel-lockhead.png`. Preserve its upward threshold, pointer capture, `pointerup` final coordinate correction, unlock backend acknowledgement and rejected-unlock recovery.

Requirements:

- When both Clock penguins are visible, upward swipe on the lockhead must still unlock exactly as before.
- Alarm swipe must not invoke `unlock` even when a pointer event bubbles to the lockscreen root.
- Timer tap must not start an unlock gesture.
- A partial alarm drag must not move the unlock handle; a partial unlock drag must not shift an alarm icon.
- A two-finger/overlapping contact sequence must not cause pointer IDs to cross. Either handle multi-touch safely with one owner per pointer or reject secondary pointer interaction without corrupting the primary gesture.
- Lockscreen background click, charging/console indicators and transport icons must not accidentally begin unlock.
- After every cancel/dismiss/snooze/unlock the CSS transform, pointer capture and gesture state must be clean.

Add a touch diagnostic receipt that logs gesture type, pointer ID, start/end coordinate, threshold result and occurrence ID, but never logs private labels or unrelated user content.

## 3.5 Ringing animations

Keep the existing successful shaking effect. Do not remove it. Verify it remains visible at the requested new positions and does not become a permanently running animation when idle.

- Alarm penguin shakes strongly only while an alarm occurrence is ringing; stop shaking immediately after the current occurrence is acknowledged/snoozed.
- Timer penguin shakes while its expired timer is ringing; stop after timer stop acknowledgement.
- Respect `prefers-reduced-motion` and system reduced-motion configuration. In reduced mode, use a static highlight/state badge rather than an infinite animation.
- Avoid animated filters/large blurred shadows; prefer transform/keyframes on a small PNG. Pause decorative animations when the display is off if they would otherwise force rendering work.

---

# 4. Doom: sound enabled by default and working menu

## 4.1 Source-level issue to inspect immediately

The supplied repository snapshot's `pwa/nuxel-apps/doom/js/doom.js` currently defines:

```js
const DEFAULT_SETTINGS = {
  sound: true, haptics: true, strafe: true, leftHanded: false, turnSensitivity: 1.0,
};
```

But its Chocolate Doom argument list includes `'-nomusic'` unconditionally, then adds `'-nosound'` only if `settings.sound` is false. This means a UI state saying `SOUND ON` can still deliberately suppress all game music. The audio path may have additional WebKit/SDL issues, but this is a concrete contradiction to remove and test. Confirm that the live deployed Doom source still contains this flag before patching; the ZIP snapshot is older than the reported deployment.

## 4.2 Sound behavior

- Fresh install/default settings must initialize to `sound: true`. Existing persisted user choice remains respected; do not override an explicit saved OFF selection during migration.
- The Play action is a trusted user gesture. Use it to unlock/resume the Web Audio / SDL audio context if the WASM build requires it. Do not attempt to play audio during page load and assume browser autoplay will permit it.
- When sound is ON, do not pass `-nosound` or `-nomusic` to the engine unless a separately documented and user-selected effect-only mode exists. `-nomusic` must not be unconditional.
- Inspect the WebAssembly build's SDL audio backend, audio callback, AudioWorklet/WebAudio implementation and `Module` initialization lifecycle. Ensure the sound device/context is created before the game starts and its promise/error is handled.
- If WebKitGTK requires a user gesture to start audio, bind initialization synchronously to the user's Play button before awaiting WAD data/engine compile. Do not lose the activation token after a chain of asynchronous operations if the browser requires immediate activation.
- If engine initialization can begin before sound is unlocked, show an explicit `Tap to enable game audio` control that performs the audio-context resume on a trusted gesture. Never silently display sound ON while actual output is muted.
- The sound toggle must update the live engine's sfx/music state if supported. If engine setting cannot change during gameplay, say so and apply it to the next session; don't make a UI toggle that only changes localStorage.
- Add safe volume controls only if the current engine supports them. Keep the system volume authoritative; do not silently force speaker volume to maximum.
- Check for `-nosound`, `-nomusic`, disabled MIDI support, missing `SDL_OpenAudio`, missing audio backend build flags, `AudioContext.state === 'suspended'`, mute/zero gain and output route failures.
- Verify **both** sound effects and music independently. A short in-game sound effect (weapon/door) and actual game music must be audible. If MIDI/music is unsupported by this build, build/enable the legitimate audio backend or document exactly what is missing; don't claim complete sound because one effect plays.
- Keep Doom user-supplied WAD licensing/provenance intact. Do not bundle proprietary game audio/music outside user-authorized data.

Add a small diagnostics section to Doom's About or a debug panel showing engine sound enabled/disabled, audio context state, audio backend initialization and most recent audio error. Do not expose excessive technical clutter during normal gameplay. Write diagnostic information to a bounded log without capturing private app content.

## 4.3 Menu control semantics

There are distinct buttons in the current source family:

- `btn-pause` is the gameplay HUD action labelled `MENU` and calls `pauseEngine()`.
- `btn-menu` is the pause-screen action labelled `RETURN TO LAUNCHER` and calls `showLauncher()`.
- `btn-resume` returns from pause to the running engine.
- `btn-quit` exits Doom back to Nuxel Home.

The owner says the menu button still does not work. Re-test the current DOM and live source rather than assuming the existing event listener is enough. Verify:

1. The gameplay HUD `MENU` button receives pointer/click input above the canvas and right joystick.
2. It pauses the WebAssembly main loop, releases all held keys/pointers, hides HUD/game controls, and reveals the pause screen.
3. `RESUME` resumes the same engine state with controls reinitialized and no stuck keys/audio.
4. `RETURN TO LAUNCHER` returns to the Doom launch/WAD screen. If the WASM module cannot be safely reinitialized, reload the PWA document once after the return action and ensure it returns to the app shell rather than leaving a blank WebView.
5. `EXIT DOOM` returns to Nuxel Home and releases immersive/orientation state.
6. No event propagation from the button is swallowed by the canvas or a transparent touch overlay.
7. All menu buttons remain usable at phone portrait/landscape dimensions, with keyboard hidden and minimum thumb-target sizes.

Add automated tests for button listeners/state transitions and physically tap every control on the S10+.

---

# 5. Launcher: reliable app icon move mode

## 5.1 Current reported failure

The desktop already supports add, resize and delete actions, but a long press on an application icon still does not allow the owner to move that icon to another grid cell. A fallback **Move** button must exist in the existing action row with Resize/Delete so the operation does not depend exclusively on a long-press drag recognizer.

Inspect current live layout implementation first. The ZIP contains `pwa/nuxel-home/js/launcher.js`, `css/launcher.css`, a `test-launcher-drag.js` test and earlier native launcher code, but 84000 later added a newer `desktop-layout.js` model. Use the live source. Do not replace the newer model with the ZIP's older implementation.

## 5.2 Required interaction

- Long-press an app icon opens the same edit/action bar used for its other icon operations.
- Action bar has explicit **Move**, **Resize**, and **Delete/Remove** controls (plus existing supported actions). The Move action must actually enter a move state.
- In move mode, app icon is visibly attached to the finger while dragging.
- The candidate drop cell is highlighted; the icon snaps to the grid when released.
- If the user releases over an occupied cell, use the grid's existing collision policy: reject with a clear snap-back, or swap only if that behavior is deliberately supported and tested. Never overlap two icons or a widget.
- Cancel/Escape/back or tapping a cancel control returns the icon to its previous cell.
- Persist new position atomically and restore it after launcher reload, app restart and reboot.
- Do not confuse `pointerdown`, `contextmenu`, long-press timer and click. A drag must not accidentally launch the app or open context menu.
- Add touch, mouse and stylus/pointer support as appropriate, with proper `pointercapture`, `pointercancel` and cleanup.

## 5.3 Preserve the multi-desktop contract

If the current launcher supports multiple desktops and edge-dragging an object between desktops, retain it. A moved icon must keep its `app_id`/stable identity; only its grid cell/desktop ownership changes. On a one-second edge dwell, switch to the adjacent desktop while retaining the dragged icon under the finger. On release, persist the new desktop and cell. Do not move an icon's executable/package association or duplicate it accidentally.

## 5.4 Move button fallback

The owner specifically requests an explicit Move control in the action bar. This is mandatory even if direct long-press drag is improved. The Move button should:

1. Close or retain the action bar according to the existing edit-mode design.
2. Enter keyboard/touch navigation or pointer drag mode clearly.
3. Show the icon's current and target cell.
4. Enable direct drag or directional step movement with a visible confirmation action.
5. Support cancel and preserve the previous location if the move is aborted.

Do not implement a “Move” button that merely changes an internal class but never offers a real move operation.

---

# 6. Widgets: long-press action bar and real drag

## 6.1 Current reported failure

Widgets can be placed/resized/deleted in some states, and earlier work added an edge-transfer model, but holding a widget still does not activate the same edit/move experience as application icons. Add a matching widget action bar and make drag/resize/remove/desktop assignment functional.

## 6.2 Widget action bar

A long-press on a widget surface (not an interactive button/input inside the widget) must enter widget edit mode and show a floating/action row with:

- **Move**
- **Resize**
- **Remove**
- **Move to desktop** or edge-drag transfer if the common desktop model provides it
- **Done/Cancel** as needed

Do not hijack normal button taps, checkboxes, note links, calendar actions, clock controls or scroll gestures inside the widget. Use a press-duration threshold and movement slop. If the finger moves before the long-press threshold, cancel the long-press and allow normal scroll/interaction. Use a clear visual selected/dragged state.

## 6.3 Move behavior

- Entering Move mode lets the entire widget follow the finger, using pointer capture and compositor-friendly transforms.
- Snap to the shared desktop grid on release.
- Respect its stored width/height and prevent overlap with icons, other widgets, dock, status bar and system navigation areas.
- On collision, show a valid-drop preview and reject/snap back if no valid cell is available. Never silently overwrite another object.
- Retain per-widget desktop ownership. A widget moved from Desktop 1 to Desktop 2 must disappear from Desktop 1 and exist exactly once on Desktop 2 after refresh/reboot.
- Edge-drag switch follows the existing dwell rule (currently expected to be approximately one second if that remains the live contract). Keep the widget visually attached to the finger during the switch; do not cancel the drag or drop it prematurely.
- Persist changes durably and notify any active desktop view to update.

## 6.4 Resize and remove

- Resize control exposes valid grid sizes. Enforce minimum/maximum dimensions per widget kind and current viewport.
- Resizing must not cause negative, fractional, out-of-bounds or overlapping geometry.
- Remove asks for confirmation if the widget has user data or may be destructive; ordinary removal should remove the placement, not delete the underlying Notes/Calendar/Clock data.
- Cancel returns to prior geometry and placement.
- A widget action bar is itself draggable only if the current UI explicitly supports that; it must not lose controls offscreen.

## 6.5 One shared model

Apps and widgets should share the same grid occupancy/collision/layout service. Preserve each item's stable ID, kind, desktop ID, cell coordinates, width/height and z-order. Do not maintain separate inconsistent collision maps. If 84000's `desktop-layout.js` or equivalent is deployed, extend and repair it. Add schema migration for older saved placements.

---

# 7. Boot and loading animation repair

## 7.1 Understand the two different animations first

Nuxel has more than one animation path. Do not confuse them or replace one with another indiscriminately.

### A. Early boot / framebuffer-native spinning penguin

The canonical source is `assets/nuxel-boot-animation.mp4`. The repository's existing boot animation documentation describes a preprocessed, packed animation container (`nuxel-animation.nux`) and a freestanding AArch64 `nuxel-anim-player` that writes to `/dev/fb0` during the early boot stage. The old docs record the source MP4's SHA-256 as:

```text
280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c
```

The existing approach exists because the S10+ downstream kernel historically exposed fbdev and not a DRM/KMS device suitable for Plymouth. The packed animation player was designed to render at the panel's source frame cadence while bounding memory and writing all virtual framebuffer buffers. It must only own fbdev during the stage for which it was designed.

### B. Wayland pre-lockscreen cinematic overlay

The canonical clip is `assets/nuxel-preloading-screen.mp4`. The repository includes `services/nuxel-preload-cinema/nuxel-preload-cinema`, `nuxel-preload-cinema.service`, and `configs/nuxel/boot/preload-cinema.json`. This path starts `mpv` as a Wayland client (historically `vo=wlshm`) after Wayland and `nuxel-wl-fb` exist. It overlays the real lockscreen while it initializes, then exits and reveals the lockscreen when readiness and media EOF/bounded conditions are satisfied.

The preloading asset is documented as H.264 High, 1080×1920, 24 fps, 6.016 seconds, with muted/unused AAC audio. Its older configured hash is:

```text
b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1
```

Recompute current hashes; do not assume assets/config remain unchanged.

**Critical display invariant:** during the active Wayland session, `nuxel-wl-fb` remains the only `/dev/fb0` writer. The early `nuxel-anim-player` may take over fbdev only in its defined early-boot stage and must hand it back safely before the Wayland framebuffer bridge takes ownership. Do not start a second fbdev painter during Wayland or make mpv write directly to `/dev/fb0`.

## 7.2 Diagnose the frozen frame

The owner reports that during the Wayland-loading transition a single static frame from `nuxel-preloading-screen.mp4` remains visible. The video has regressed and does not play properly. Determine exactly which surface/player is showing that frame:

- HTML `<video>` poster/cover from the launcher PWA?
- `nuxel-preload-cinema` `mpv` Wayland overlay?
- `nuxel-wl-fb` last-frame cache or fbdev handoff?
- early initramfs animation first-light frame?
- a static `preload-cover` image retained because the video player fails or the ready marker is stale?
- a service-worker cache returning an old document or asset?
- an mpv instance that created a surface but is paused at frame 0 or cannot advance due the wrong output/socket/runtime?

Inspect all relevant code and receipts. Current preload controller documentation describes readiness gates such as `/run/nuxel-launcher-ready`, `/run/nuxel-home.state`, `/run/nuxel-wl-fb.state`, a fresh `/var/lib/nuxel/display` receipt, and touch readiness. Touch readiness is not supposed to hold the final frame. Confirm the current runtime version and exact gates.

Collect:

- `systemctl status/cat/journalctl` for the preload controller and session.
- Controller receipt and log, mpv process command line and stderr.
- Current Wayland socket, `XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY`, UID/GID, cgroup and mount namespace.
- mpv IPC commands/responses: `get_property path`, `time-pos`, `duration`, `pause`, `eof-reached`, `estimated-vf-fps`/stats where available.
- Frame counter/decoded-frame evidence or periodic screenshot checks showing different actual frame content at two timestamps.
- Asset path, SHA-256, file size, `ffprobe` stream metadata, full decode test and file permissions.
- Service worker / PWA cache version and URL query versions.
- `nuxel-wl-fb` ownership state, geometry, refresh/pan receipts and whether the last committed image actually changes.

Do not conclude that a video is playing because an mpv PID exists or a Wayland surface appears. Verify moving frames.

## 7.3 Desired stage transition

The requested temporary behavior is:

```text
EARLY BOOT
  spinning penguin: existing boot animation pipeline
       |
       v
WAYLAND / SESSION STARTING (the interval that currently shows a frozen frame)
  spinning penguin: loop the existing nuxel-boot-animation visual
       |
       v
WAYLAND + nuxel-wl-fb + NUXEL HOME PRESENTATION READY
  transition cleanly to the existing nuxel-preloading-screen.mp4 cinematic
  if that is still the desired current visual sequence; otherwise reveal the
  real lockscreen as soon as readiness policy says so
       |
       v
PRELOADING CLIP EOF / bounded completion + real lockscreen ready
  close media client, remove cover/overlay, reveal real lockscreen
       |
       v
LOCKED NUXEL HOME
```

The owner explicitly asks that the **Wayland-loading static-frame interval** use the spinning penguin from `nuxel-boot-animation.mp4` for now, in a loop. This is not permission to replace the canonical source asset, corrupt the real preloading clip, or add an unbounded cover.

Recommended implementation:

1. Identify the component that owns the Wayland-starting visual and add an explicit `WAYLAND_STARTING`/`WAYLAND_READY` stage to the existing boot/session presentation state machine.
2. Use the already-generated packed `nuxel-animation.nux` + AArch64 `nuxel-anim-player` only if that exact stage is still before Wayland takes fbdev ownership. Verify actual handoff and the current build artifact/hash.
3. Once Wayland is running and `nuxel-wl-fb` owns the physical framebuffer, present the spinning penguin as a normal Wayland client/overlay using the supported current media player path. If the mpv build can loop the 8-second H.264 clip smoothly at this stage, configure a single `--loop-file=inf`-style loop using the exact supported CLI/API for the installed mpv version. Verify it on the phone. If it cannot, use a compatible preprocessed animation renderer that targets the existing Wayland compositor, not `/dev/fb0` directly.
4. Do not use the full animation MP4 through a WebKit `<video>` until the installed WebKit/GStreamer media stack is proven. The existing preload controller docs state that WebKitGTK's media path previously failed because an absent `libgstautodetect` caused `autoaudiosink` failure; mpv over Wayland was selected for that reason. Verify current runtime before changing this decision.
5. Keep the full `nuxel-boot-animation.mp4` and `nuxel-preloading-screen.mp4` sources byte-identical. Do not recompress or crop them to hide the bug. The packed NUX artifact is a generated derivative; validate its decoder and hash independently.
6. The loop starts only in the identified Wayland-loading interval, remains visually alive, and stops as soon as the next stage is actually ready. It must never overlay an already-unlocked desktop or reappear after lockscreen dismissal.
7. When playback/controller fails, release the overlay and expose the real lockscreen/fallback. The fallback must be bounded and fail-open.

If the owner means that the Wayland startup interval should show only the spinning-penguin animation and skip `nuxel-preloading-screen.mp4` entirely, preserve the existing cinematic asset/config but disable only that stage through a clear configuration flag; do not delete the asset or break the existing handoff machinery. Document the selected stage sequence in the UI/boot docs.

## 7.4 Repair actual preloading-screen playback

The preloading clip must play moving frames and not hang at one frame. Inspect mpv options and the controller's IPC event loop. Pay particular attention to:

- Incorrect pause/resume state after `file-loaded`.
- IPC reads/writes that deadlock or miss newline-delimited JSON messages.
- The controller waiting for video EOF but mpv paused at frame 0 or unable to decode.
- A Wayland socket/runtime/UID mismatch between the session and player process.
- Wrong video output (`wlshm` vs available renderer) for the current mpv build.
- Surface configure/expose events and window geometry/scale.
- A stale asset hash/config preventing playback but leaving a poster/cover visible.
- An arbitrary startup delay or readiness timeout that never expires due a stale receipt.
- The preloading file being copied to `/usr/share/nuxel/preload/` but the live controller reading another path.
- A service worker caching old preloading page/asset references.

The repository's current config historically uses:

```json
{
  "player": "/usr/bin/mpv",
  "video_output": "wlshm",
  "audio": "never"
}
```

Treat that only as a starting point. Confirm the installed binary and actual supported options. The audio track in the preloading clip is deliberately not played; do not accidentally introduce boot audio.

Add a robust media state machine with bounded timeouts:

```text
PRECHECK -> PLAYER_STARTING -> FILE_LOADED -> FRAME_ADVANCING
          -> PLAYING -> EOF/BOUNDED_END -> RELEASED
            \-> FAILED/TIMEOUT -> FAIL_OPEN
```

The controller should publish stage, current path/hash, player PID, playback position/frame progress, readiness snapshot, EOF/timeout and fallback reason. Ensure one controller instance per boot and remove stale sockets/markers correctly. Preserve the existing session ownership behavior: the phone session starts the early controller; the systemd-only fallback must not race it or mark the one-shot done state prematurely.

## 7.5 Animation validation

Before deploy:

- Verify both canonical MP4 hashes and `ffprobe` data.
- Decode every frame offline (or validate all frames from the packed NUX decoder) and prove frame count/content differs over time.
- Verify the packed animation C decoder matches the reference decoder if the boot stage uses `.nux`.
- Unit-test mpv IPC with a fake peer and test real mpv with a generated non-sensitive moving clip if available.

On device:

- Capture lockscreen/boot surface at time T, T+0.5 s, T+1.0 s and T+2.0 s during the targeted interval; prove the penguin moves.
- Capture the preloading clip at multiple timestamps and prove it progresses.
- Verify correct aspect ratio, black/transparent letterboxing as designed, orientation and no stretched source.
- Verify no double image, tearing, black flash or flicker during owner handoff.
- Confirm `nuxel-wl-fb` remains sole `/dev/fb0` writer during Wayland. Check process/owner receipts before, during and after each stage.
- Test rapid boot, slow boot, missing clip, corrupt clip, mpv crash, delayed Wayland, delayed touch and unlocked-session startup.
- Verify every fallback releases its overlay within a hard upper bound and does not leave a static frame stuck forever.

---

# 8. Cross-cutting tests and regression protection

## 8.1 Unit and integration tests

Add or update a focused `tests/pwnage87000/` suite (or project-native equivalent). Tests should include:

### Clock schema/scheduler

- one-shot future alarm appears in status.
- one-shot expired/completed alarm does not appear as upcoming.
- weekly alarm for each weekday computes the next correct occurrence.
- all seven checked days are stored as seven values; unchecking all is invalid.
- disable/enable updates indicator state immediately.
- deleting the final alarm removes the indicator.
- a currently ringing occurrence remains represented until acknowledged.
- snooze persists across service restart and fires again at the requested interval.
- dismiss current occurrence leaves other alarm definitions/occurrences intact.
- migration from legacy `repeat` bool preserves daily behavior and does not lose alarms.
- duplicate scheduler ticks cannot play the same event twice.
- timezone/DST edge cases do not skip or double-fire an occurrence.

### Sound contract

- alarm cue and timer cue resolve different sound IDs/paths.
- play request -> playing state -> actual playback backend stream lifecycle.
- stop timer only stops matching timer playback; alarm cue continues.
- stop alarm occurrence only stops its playback; another queued occurrence remains.
- invalid path, missing asset, no PipeWire socket, wrong session UID, sink unavailable and backend process exit produce explicit failed state.
- default assets and independent sound settings persist.

### Lockscreen

- timer and alarm anchor positions use CSS/measured layout variables.
- alarm pointerdown/move/up updates visual transform and dispatches one left/right action at threshold.
- cancel returns to neutral.
- timer one-tap dispatches stop once.
- unlock pointer sequence still reaches host unlock action with both Clock indicators visible.
- one pointer cannot be claimed by two interaction owners.
- no false unlock from alarm swipe and no alarm dismissal from unlock swipe.
- all indicators hide/show from authoritative service state.

### Doom

- default sound on; explicit saved off respected.
- arguments contain no unconditional `-nomusic` and no `-nosound` when enabled.
- explicit sound off produces muted configuration as intended.
- trusted Play click unlocks/resumes audio context.
- initialization error is surfaced.
- menu/pause/resume/launcher/exit transition contracts work.
- all held keys and touch pointers release on pause/exit/blur.

### Launcher/widgets

- app icon long-press shows action row; Move button enters functional move state.
- icon dragging follows pointer; grid snapping/collision/cancel persistence works.
- widget long-press action row appears only after threshold; interactive child clicks still work.
- widget Move/Resize/Remove work; object ID/data remains intact.
- app/widget grid occupancy is shared; no overlap after moves/resizes.
- edge-dwell desktop transfer retains the dragged object under the pointer.
- reload restores desktop positions/ownership.

### Boot/preload

- controller stage state transitions and timeouts.
- no early boot animation process after Wayland fb owner takes over.
- session-owned preload controller does not race systemd fallback.
- mpv IPC frame advancement and EOF detection.
- crash/missing asset/readiness failure releases overlay.
- stale marker/receipt cleanup on each new boot.
- no player overlay after unlock.

## 8.2 Static checks and project gates

Discover the actual current Makefile/pytest/Node test targets. Run focused tests first, then the relevant complete suite. At minimum:

- Python syntax and unit tests for clockd/soundd/preload controller.
- JavaScript syntax checks for Clock, lockscreen indicators, Doom, launcher and widgets.
- Existing Doom touch and engine test suite.
- Existing lockscreen unlock/indicator test suite.
- Existing launcher drag/desktop-layout tests.
- Existing preload cinema/boot animation tests.
- Full project test gate available in this checkout, without claiming unrelated suites were run.
- `git diff --check`, source hashes and packaging/manifest validation.

Do not weaken existing assertions to make the suite green. Update a test only when the old contract was deliberately superseded, and document why.

## 8.3 Versioned PWA assets and cache

The shell uses cached PWA assets. For every changed script, CSS, HTML or JSON:

- update the cache-busting query/version or service-worker precache version consistently;
- remove obsolete cache references carefully;
- ensure the active home iframe and app document load the new version;
- verify the live phone actually received the new asset hash;
- do not use a hard browser cache clear that discards important app data.

A successful copy into `/usr/share/nuxel` is not enough if the service worker serves the old script.

---

# 9. Deployment and rollback

## 9.1 Backup before every persistent change

Create a timestamped backup on the phone under:

```text
/var/backups/nuxel/pwnage87000-<UTC_TIMESTAMP>/
```

Back up every target file, asset, config, systemd unit/drop-in, service state schema, sound preferences and desktop layout state that will be modified or migrated. Preserve owners, groups, modes, symlinks and xattrs where applicable. Store a manifest with original SHA-256 values. Do not copy private keys, browser cookies or credential stores into the backup/evidence folder.

Before a migration, create a consistent copy of the source data and a schema-version receipt. Make the migration idempotent and reversible; never discard old data until the new data is verified and a recovery copy exists.

## 9.2 Deploy in bounded groups

Suggested order:

1. Source tests and schema migrations offline.
2. Clockd/soundd service changes and cue mapping; deploy without touching boot/animation.
3. Clock UI + lockscreen overlay/gesture; restart/reload the narrow PWA/bridge path.
4. Doom assets/scripts and launcher cache update.
5. Launcher/widget changes and layout migrations.
6. Preload controller/config/assets; verify before changing early boot or initramfs.

For each group, copy to a temporary staging path, verify hashes, atomically replace, set proper ownership/mode, run import/syntax checks, reload/restart only necessary units, and collect status. Do not combine unrelated risky changes into one large unverified overwrite.

## 9.3 Reboot gate

Most requested repairs are userspace/PWA/service changes and should not require a kernel/bootloader flash. Do not flash kernel, boot, recovery, super, userdata or repartition anything for these bugs.

If a reboot is necessary for a service/session change:

- confirm the current backup is readable and checksummed;
- confirm recovery path (TWRP/USB) and the known-good boot image remain untouched;
- confirm Wi-Fi SSH startup behavior and the phone is on stable power;
- save before-reboot service/layout/schedule state;
- reboot once, reconnect over Wi-Fi SSH using the same verified key/known-host procedure, and compare after-boot state;
- do not repeatedly reboot or start boot experiments without new evidence.

If a future change truly requires a boot image/initramfs update to use the original animation player, stop and prepare a separate exact procedure with partition, image hash, backup and recovery evidence. Do not flash as part of this round without an explicit proven requirement and safety gate.

## 9.4 Rollback

Provide exact commands to:

- restore changed PWA/bridge/daemon files from the timestamped backup;
- restore units/configs and daemon state schema where safe;
- restore prior Clock data and selected sounds if a migration caused regression;
- revert launcher/widget layout model and restore layout JSON;
- restore prior preload configuration and assets;
- re-run `systemctl daemon-reload` only when unit files changed, then restart affected services;
- verify the phone returns to the previous working lockscreen, audio and launcher state.

Rollback must not erase newly created user alarms, notes, widgets, desktop layout or other data unless the owner explicitly chooses to revert that data. Prefer schema rollback/forward compatibility and preserve new user state.

---

# 10. Physical-device acceptance matrix

The following must be performed on the actual S10+, not merely in a browser VM or headless test:

| Area | Scenario | Expected proof |
|---|---|---|
| Alarm sound | One-shot alarm, screen on + locked | Audible selected alarm sound; `clockd` occurrence and soundd playback IDs match |
| Alarm sound | Alarm due while display off | Physical speaker audible; event logs show route available/activated; screen need not be unlocked |
| Timer sound | Timer expires while locked | Audible timer sound; independent timer occurrence/playback ID |
| Sound isolation | Timer stop while another alarm is scheduled/ringing | Timer playback stops only; alarm remains correct |
| Alarm snooze | Swipe left | Penguin follows finger; icon snaps/acknowledges; same occurrence snoozes and rings again after configured interval |
| Alarm dismiss | Swipe right | Penguin follows finger; only current occurrence is dismissed; other alarms remain scheduled |
| Alarm indicator | Disable all alarms | Alarm penguin disappears immediately |
| Alarm indicator | Enable future one-shot or weekly alarm | Indicator appears; remains after app close/relock/reboot as applicable |
| Alarm recurrence | Check Mon–Sun independently and save | Exact selected days persist and next occurrence matches local time |
| Timer indicator | Timer expires, tap penguin | Timer sound stops and icon disappears after acknowledgement |
| Unlock | Both Clock icons visible | Existing lockhead upward drag still unlocks; no gesture conflict |
| Doom sound | Fresh/default launch | Sound effects and music are audible after Play gesture; setting shows ON |
| Doom menu | During gameplay tap MENU | Pause menu visible; no stuck input/audio |
| Doom resume | Tap Resume | Same game continues; controls/audio work |
| Doom launcher | Tap Return to Launcher | Start screen returns, engine state cleaned/reloaded safely |
| App move | Long-press icon -> Move -> drag -> release | Icon follows finger, snaps to new grid cell and persists |
| App move fallback | Use Move button instead of drag recognition | Same successful move result |
| Widget edit | Long-press a widget | Action bar appears; child controls remain usable under ordinary taps |
| Widget move | Move/resize/remove | Correct geometry and state; no overlap; persists |
| Boot loading | Cold boot through Wayland startup | Spinning penguin visibly advances/loops rather than one static preloading poster |
| Preload video | Wayland overlay clip | Actual moving frames from `nuxel-preloading-screen.mp4`; no freeze; bounded release to lockscreen |
| Boot handoff | Lock screen becomes ready | One display owner; no tearing, stuck overlay, black screen or late cover |
| Failure fallback | Simulated missing/corrupt clip or mpv failure | Safe lockscreen/fallback appears within configured hard deadline |

Document which physical tests were performed, by whom and at what time. If operator interaction is required, create a minimal touch checklist and use the owner to execute it; do not mislabel it as passed before the physical result is reported.

---

# 11. Evidence and final engineering report

Create:

```text
docs/pwnage-87000/evidence/<UTC_TIMESTAMP>/
```

Include:

- `ENGINEERING-REPORT.md` — full narrative and outcome.
- `baseline/` — source status, service state, versions, hashes, process list and current schedule/layout snapshot (redacted).
- `commands/` — relevant command transcripts with secrets filtered.
- `journals/` — exact clockd/soundd/PipeWire/Wayland/preload excerpts.
- `audio/` — cue event IDs, playback status, sink state, timing and non-sensitive measurements; do not include private microphone recordings.
- `lockscreen/` — screenshots/captures and pointer trace proving layout, drag-follow and unlock isolation.
- `doom/` — engine argument receipt, audio init status, menu state transitions and physical test notes.
- `desktop/` — before/after layouts, move/resize/collision receipts and test outputs.
- `boot/` — media metadata, hashes, mpv IPC/frame progress, stage receipts, multiple frame captures and owner/handoff state.
- `tests/` — exact test commands and results.
- `rollback/` — backup manifest, hashes and exact rollback script/commands.

The final report must separate:

- Implemented in source.
- Deployed to the S10+.
- Automated tests passed.
- Verified physically by audible sound/touch/visible moving frames.
- Not verified or blocked, with evidence explaining why.

Do not inflate test counts, omit failures, or claim a playback event was audible based only on a daemon acknowledgement.

---

# 12. Completion criteria

PWNAGE-87000 is complete only when all of the following are true:

1. A real system-scheduled alarm is audibly heard on the S10+ speaker when the phone is locked, including while the display is off; the event and playback IDs can be traced end-to-end.
2. A real timer is audibly heard and can be stopped by tapping its penguin, with alarm sound/state left independent.
3. Alarm penguin follows the finger during swipe, is in the requested position, disappears when no enabled future alarm exists, and its left/right semantics work without disturbing unlock.
4. One-shot and weekly alarms with seven independently configurable days can be created, edited, toggled and persisted. Snooze re-rings and dismissal affects only the current occurrence.
5. Doom starts with enabled sound by default (unless the user has deliberately saved it off); actual sound effects and music work, and Menu/Pause/Resume/Return/Exit all work on device.
6. App icons can be moved by long-press drag and by an explicit Move button. Widgets have a real long-press action bar and can be moved/resized/removed. No overlap or data loss occurs.
7. The Wayland-loading interval shows a real moving loop of the spinning-penguin asset, not a static frame; the preloading-screen clip plays through moving frames and exits to the actual lockscreen within a bounded time.
8. All relevant existing tests and new PWNAGE-87000 tests pass, with no regression in boot, display, touch, audio, app launch or existing data.
9. Backup, hashes, evidence and tested rollback are present.

If one item cannot be physically verified because of a confirmed hardware limitation, report the exact limitation and all completed work honestly. Do not say “fully done” while a required physical behavior remains unverified.

**Now execute this specification. Start with Wi-Fi SSH root reconnaissance, proceed through all workstreams, deploy safely, test on the real phone, and write the evidence-backed engineering report.**
