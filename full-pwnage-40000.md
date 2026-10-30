# FULL-PWNAGE-40000
# NUXEL S10+ — FINAL BUILT-IN SPEAKER AUDIO REPAIR
## ACTUAL SPEAKER OUTPUT, HUMAN AUDIBLE CONFIRMATION, ITERATIVE FIXING AND PERSISTENCE

**Mission:** PWNAGE-40000 FINAL SPEAKER FIX
**Target device:** Samsung Galaxy S10+ SM-G975F / beyond2lte
**SoC:** Exynos 9820
**OS:** Nuxel Fedora-based ARM64 Linux
**Kernel:** Existing installed kernel — do not replace or flash
**Access:** Existing Wi-Fi SSH
**SSH key:** Use the working key and target from the latest deployment; current archive records `~/.ssh/wicked_wqn_id_rsa` and `root@192.168.178.167`. Verify the actual working address and route before connecting.
**Source asset:** `./assets/nuxel-pow.mp3`
**Deployed asset:** `/usr/share/nuxel/assets/nuxel-pow.mp3`
**Target output:** Physical built-in loudspeaker, not earpiece, headphones, Bluetooth or USB.

---

# 0. THE MISSION

Previous PWNAGE-40000 work has successfully repaired much of the S10+ audio initialization and playback infrastructure.

The latest uploaded repository contains live evidence that:

- The ABOX Calliope core can reach `MUB0`.
- Both CS35L41 DSP1 protection processors can reach `booted=Y running=Y`.
- The ABOX RDMA1 gate can be enabled.
- The complete RDMA1 → SPUS → SIFS1 → UAIF1 route can be programmed.
- Left and right amplifier PCM gains can be set to 12.
- PipeWire can create and select the static RDMA1 sink.
- The actual ALSA hardware stream can run at 48 kHz.
- The hardware pointer can advance during playback.
- `pw-play` can decode and complete the POW asset.
- The startup sound service can run after a route readiness gate.

Yet the latest report explicitly does not claim that the physical speaker has been heard and confirmed.

**Your mission is to finish the remaining speaker output problem, not to repeat every completed audio initialization task.**

We know actual sound was previously audible during live experiments, including diagnostic tones and Nuxel POW playback.

Therefore:

- Do not assume the hardware is fundamentally broken.
- Do not discard the existing working path.
- Do not make a TWRP reflash the first response.
- Do not rebuild or replace the kernel without compelling new evidence and separate authorization.
- Investigate the missing speaker-specific route and output-level conditions first.
- Keep iterating until the owner confirms physical sound through Notes.

This mission is not complete until the owner hears the POW and confirms it.

---

# 1. WHAT THE CURRENT REPOSITORY ALREADY PROVES

The latest archive contains:

- `audio.md`
- `docs/beta-finalization/live/PWNAGE-40000-TODO.md`
- `docs/beta-finalization/live/PWNAGE-40000-REPORT.md`
- `docs/beta-finalization/live/evidence/pwnage-40000/FINAL-REPORT.md`
- `docs/beta-finalization/live/evidence/pwnage-40000/SOURCE-RECONCILIATION.md`
- Two live continuation runs and their device logs.
- The deployed-route source.
- The Notes confirmation detector.
- PipeWire and WirePlumber configuration.

Read these before changing anything.

## 1.1 Current verified hardware path

The latest report records:

| Component | Verified state |
|---|---|
| ABOX Calliope | `MUB0` |
| CS35L41 DSP1 left | `booted=Y running=Y` |
| CS35L41 DSP1 right | `booted=Y running=Y` |
| ABOX RDMA1_EN | `1` |
| ABOX SPKAMP_EN | `1` |
| ABOX SPKAMP_A | `2` / RDMA1 |
| ABOX SPKAMP_B | `2` / RDMA1 |
| Left/Right AMP PCM Gain | `12 / 12` |
| PipeWire sink | `alsa_output.hw_0_1` |
| Sink format | `S16LE, 2 channels, 48000 Hz` |
| Default sink | `alsa_output.hw_0_1` |
| RDMA1 stream | `48000 Hz` |
| Hardware pointer | Previously observed advancing during playback |
| Startup cue | Attempted once after readiness |

These are valuable completed milestones.

Do not rebuild this architecture unless a live check shows it has regressed.

## 1.2 The remaining distinction

The evidence shows successful playback through parts of the software and hardware pipeline.

It does not prove:

- Correct ABOX speaker sound mode.
- Correct channel-to-physical-speaker selection.
- Correct final amplifier output.
- Audible sound reaching the owner.

The new mission must focus on those final missing stages.

---

# 2. PRIORITY ROOT-CAUSE HYPOTHESIS — ABOX SOUND TYPE

## 2.1 The control found in the repository

The archived ALSA mixer snapshot contains:

`ABOX Sound Type`

Its actual enumerated choices are:

```text
0 = VOICE
1 = SPEAKER
2 = HEADSET
3 = BTVOICE
4 = USB
5 = CALLFWD
```

The earlier live correction in:

`docs/beta-finalization/live/evidence/pwnage-38000/audio-fix-20261029c.txt`

explicitly set:

`ABOX Sound Type = 0`

This was described as:

`VOICE, the boot default`

However, our actual output objective is the phone's built-in loudspeaker.

## 2.2 The persistent route script omits this control

Inspect:

`services/nuxel-s10/bin/nuxel-audio-route.sh`

The current route implementation applies and verifies:

- ABOX RDMA1_EN.
- SPKAMP_EN.
- SPKAMP_A/B.
- Amplifier enables.
- Amplifier unmute state.
- DSP1 firmware and preload.
- Amplifier PCM gains.
- PCM Source.
- SPUS routing.
- SIFS1 routing.
- UAIF1 routing.
- PipeWire sink and rate.
- Default sink.
- Volume cap.

But it does not set or verify:

`ABOX Sound Type`

This is a significant gap in a speaker-specific route.

## 2.3 FIRST TARGETED EXPERIMENT

Before changing unrelated controls, capture the actual live value and allowed choices.

Then test:

`ABOX Sound Type = SPEAKER`

Use the actual enumerated name if supported:

```bash
amixer -c CARD cset name='ABOX Sound Type' SPEAKER
```

If the driver only accepts an index, use the verified index:

`1`

Immediately read the control back by name.

Record:

- Previous mode.
- New mode.
- Actual readback.
- Other affected mixer controls.
- DAPM changes.
- PipeWire state.
- Audio route readiness.

Do not assume that the write succeeded just because the command returned zero.

Do not set the persistent route permanently until the owner confirms that this mode actually produces audible speaker output.

If it does, add `ABOX Sound Type=SPEAKER` to:

- The persistent route application.
- The readback validation.
- The boot readiness gate.
- The diagnostic output.
- The relevant regression tests.

If it does not, continue controlled investigation and retain the ability to restore the previous value.

**This is the first major experiment because the previous route used VOICE while the current requirement is SPEAKER.**

---

# 3. PHYSICAL OUTPUT MAPPING — RIGHT AMP SPEAKER, LEFT AMP RECEIVER

The repository's live DAPM evidence identifies two separate output paths:

- `Right AMP SPK` → `SPEAKER`
- `Left AMP SPK` → `RECEIVER`

Both have previously reported their DAPM widgets ON.

This distinction matters.

The goal is the external built-in loudspeaker, not merely the receiver/earpiece.

Inspect the current real DAPM graph and map the physical output path.

Verify:

- Right amplifier output connects to the physical SPEAKER endpoint.
- Left amplifier output connects to the RECEIVER endpoint.
- The expected channel is delivering audio samples.
- The correct amplifier remains enabled.
- The correct amplifier is unmuted.
- Its DSP1 is booted and running.
- Its PCM Source is correct.
- Its output selection is correct.
- Speaker-specific routing is active.

Do not treat a DAPM widget being ON as proof of audible sound.

## 3.1 Inspect channel content

The archive's `nuxel-pow.mp3` asset is:

- 44.1 kHz.
- Stereo.
- Approximately 0.366 seconds.
- Both channels contain very similar audio content.

The source file is not obviously corrupt.

Nevertheless, verify the installed asset checksum and decoded signal.

Inspect the PipeWire stream's actual channel map and channel delivery.

Ensure the channel mapped to the right amplifier and physical SPEAKER path is not silent, muted or discarded.

Do not change channel mapping blindly.

Test the physical right-speaker path first.

If necessary, use controlled one-channel routing experiments with the same supplied POW asset, while preserving the original route for rollback.

Do not use a receiver-only success as proof of speaker success.

---

# 4. PRESERVE THE KNOWN-GOOD AMPLIFIER GAIN

This is already a measured correction.

The latest report identifies:

- Gain 19 logs `GAIN_CTRL = 0x273`.
- Gain 12 logs `GAIN_CTRL = 0x193`.
- The cold-boot default 19 was associated with silence.
- The corrected persistent route now sets 12.

Inspect:

- `Left AMP PCM Gain`
- `Right AMP PCM Gain`

Verify both are currently 12.

Do not blindly raise these mixer controls.

Do not bypass CS35L41 protection.

Do not disable thermal protection or DSP1 protection firmware.

The current value 12 is the known-good starting point and should remain unchanged while investigating ABOX mode and PipeWire routing.

If a different physical amplifier gain is genuinely required, establish it from the actual allowed range and driver semantics, use a reversible controlled test, and record the precise evidence.

Do not guess.

---

# 5. VERIFY THE CORRECT PIPEWIRE ROUTE

## 5.1 Preserve the existing static RDMA1 sink

Inspect:

`configs/s10plus/pipewire/50-nuxel-s10-alsa.conf`

The static sink is:

`alsa_output.hw_0_1`

It uses:

- `api.alsa.pcm.sink`
- Hardware device `hw:0,1`
- S16LE
- Two channels
- 48000 Hz

This exists because the image does not use the usual udev ALSA discovery path.

Preserve it.

Do not replace it with generic autodetection.

Do not re-enable `systemd-udevd` as a shortcut.

Do not use RDMA0.

## 5.2 Use PipeWire for playback

The live system uses PipeWire 1.4.11 and WirePlumber.

PipeWire owns the RDMA1 hardware device.

Direct ALSA attempts can encounter `EBUSY`.

Use:

`pw-play`

through the actual PipeWire default sink.

The correct environment on the phone is normally based on:

```text
XDG_RUNTIME_DIR=/run/nuxel-wayland
PIPEWIRE_RUNTIME_DIR=/run/nuxel-wayland
PULSE_SERVER=unix:/run/nuxel-wayland/pulse/native
```

Verify the real runtime socket and process context before using them.

## 5.3 Default sink must be read back

The expected sink is:

`alsa_output.hw_0_1`

Verify:

1. Sink exists.
2. PipeWire native socket accepts connections.
3. Default sink is selected by stable name.
4. `pactl get-default-sink` reads back the expected node.
5. The actual test stream connects to that node.
6. The stream is linked to the expected hardware route.

Do not mistake a sink's existence for default routing.

Do not accept `null` as the default sink.

Do not ignore `_ensure_default_sink()` failure in the bridge.

## 5.4 Avoid the old GStreamer test-path failure

The prior Settings Test Audio implementation used:

`gst-launch-1.0 ... pulsesink`

and terminated before the stream was actually linked.

This path failed to produce playback samples.

The corrected implementation uses:

`pw-play`

Keep this implementation.

Do not reintroduce the old short GStreamer window as a test path.

Use one consistent playback backend for the actual speaker confirmation.

---

# 6. PIPEWIRE VOLUME — VERIFY THE REAL ATTENUATION

The existing configuration deliberately imposed a 25% default ceiling.

The relevant files include:

- `configs/nuxel/audio/audio.json`
- `configs/s10plus/pipewire/50-nuxel-s10-alsa.conf`
- `configs/pipewire/asound-nuxel-safe.conf`
- `services/nuxel-s10/bin/nuxel-audio-route.sh`
- `services/nuxel-bridge/src/hw_providers.py`
- `tools/s10plus/a33/nuxel-sound-cue.py`

## 6.1 Important implementation distinction

`configs/pipewire/asound-nuxel-safe.conf` documents an ALSA `softvol` cap for ALSA consumers that open `default`.

However, the static PipeWire sink opens:

`hw:0,1`

directly.

PipeWire therefore bypasses the ALSA `default` plugin chain.

Do not assume the ALSA softvol plugin limits the static PipeWire sink.

The actual runtime volume path must be measured.

The current Nuxel route script and bridge enforce a PipeWire sink volume ceiling of 25%.

This is separate from the amplifier digital trim.

## 6.2 Owner-authorized controlled volume ramp

The owner explicitly authorizes the necessary normal software volume changes to make the speaker audible.

Start from the current volume.

First test the current configured level.

If the owner reports no audible sound:

- Inspect the actual PipeWire sink volume.
- Verify the test player's decoder gain.
- Verify there is exactly one attenuation stage.
- Increase the PipeWire sink volume in measured increments.

Use a controlled progression, for example:

```text
25%
35%
45%
55%
65%
75%
85%
90%
100% (only if still required)
```

Each level is a separate playback test with its own 30-second owner-response window.

Do not jump directly to maximum.

Do not continuously play the file.

Do not combine high digital gain with arbitrary changes to amplifier PCM Gain.

Do not disable DSP1 protection or thermal protection.

If the owner confirms sound at a higher volume, record the exact level.

Update the persistent volume policy only as required to make ordinary Nuxel playback audible.

Do not silently lower the level back to an inaudible 25% after confirmation.

Preserve a user-adjustable volume control and document the chosen default and ceiling.

## 6.3 Avoid double attenuation

Use:

`pw-play --volume 1.0 /usr/share/nuxel/assets/nuxel-pow.mp3`

The PipeWire sink's own volume is the attenuation stage.

Do not also pass `gain_percent=25` to the player when the sink is already at 25%.

The earlier implementation multiplied these values and produced only 5% effective level.

The manual test must have exactly one deliberate attenuation stage.

---

# 7. SOUND MODE, MUTE AND PLAYBACK POLICY

Inspect:

`/var/lib/nuxel/audio/sound-mode`

The playback provider rejects sound when the current mode is:

- `silent`
- `vibrate`

Check this before every test.

For speaker testing, the system must be in normal audible sound mode.

If the existing mode is silent/vibrate:

- Record it.
- Temporarily switch to normal sound for the explicit owner-authorized test.
- Restore the intended user mode after testing unless the owner chooses otherwise.

Verify:

- Both AMP Mute controls are unmuted.
- PipeWire sink mute state is false.
- The selected sink volume is above zero.
- Nuxel sound policy permits audio.
- No extra attenuation path reduces the signal to near silence.

Do not report success when the `sound-mode` policy deliberately suppressed playback.

Do not let the manual confirmation sound trigger overlapping volume-preview or notification sounds.

During the test loop, suppress all unrelated Nuxel audio feedback.

The only audible test sound should be `nuxel-pow.mp3`.

---

# 8. HUMAN CONFIRMATION — NEW SINGLE-PLAY / 30-SECOND TEST LOOP

The previous three-POW confirmation loop is superseded.

The owner's new agreement is:

**One MP3 playback per test, followed by 30 seconds for the owner to react.**

## 8.1 Owner response vocabulary

The user will keep Notes open, with the Title field focused.

Possible responses:

| Notes Title | Interpretation |
|---|---|
| `yes` | Audible success |
| `works` | Audible success |
| `no` | Explicit audible failure |
| Empty after 30 seconds | No audible response |
| Anything else | Unknown / needs interpretation |

Comparison is case-insensitive and trims surrounding whitespace.

A positive result must be a fresh title change after the current playback test.

## 8.2 One test iteration

Every test must follow this exact sequence:

```text
CONFIRM NOTES IS READY
        |
        v
RECORD TEST NUMBER AND ROUTE
        |
        v
ANNOUNCE: TEST #N — LISTEN NOW
        |
        v
PLAY nuxel-pow.mp3 EXACTLY ONCE
        |
        v
START 30-SECOND MONOTONIC TIMER
        |
        v
WATCH NOTES TITLE FIELD
        |
        +---- yes / works ----> OWNER CONFIRMED
        |
        +---- no --------------> NEGATIVE RESULT
        |
        +---- EMPTY AFTER 30s -> NEGATIVE RESULT
        |
        v
SAVE EVIDENCE
        |
        v
IF NEGATIVE: FIX NEXT ISSUE
        |
        v
NEXT SINGLE-PLAY TEST
```

Do not play a second sound during the 30-second response interval.

Do not start the next test early.

Do not compress the 30-second window.

Do not run three or more repetitions of the sound inside one test.

## 8.3 Before each sound

The owner must know when to listen.

Print a visible message such as:

`PWNAGE-40000 TEST 07 — SPEAKER MODE / 45% — PLAYING NOW`

Start the single playback.

Then provide the full 30-second response opportunity.

## 8.4 Positive confirmation

When the new active Title contains exactly `yes` or `works`:

- Record PASS.
- Record the test number.
- Record the exact route configuration.
- Record PipeWire output volume.
- Record time.
- Record the Notes note ID.
- Record the live Title.
- Corroborate against the Notes application model/store.
- Stop changing the currently confirmed route.

Do not immediately overwrite the successful speaker settings.

Preserve the exact configuration that produced sound.

## 8.5 Negative confirmation

If the owner enters `no`:

- Record an explicit NO-AUDIBLE-SOUND result.
- Do not claim success.
- Diagnose the next failure layer.
- Change one logical variable or group of related controls.
- Validate the change.
- Play one fresh POW.
- Start another 30-second response window.

## 8.6 Empty Title

The owner has explicitly agreed that leaving the Title blank for the whole 30-second window means the sound was not heard.

However, use this interpretation only if the Notes input channel has passed its preflight.

If Notes focus, keyboard input or display state is broken, the absence of text is an input-channel failure, not evidence of audio failure.

---

# 9. NOTES CONFIRMATION CHANNEL — FIX THE EARLIER FAILURE

The archived Notes implementation provides:

- Title field: `#note-title`
- Store key: `nuxel-notes`
- Application interface: `window.nuxelNotes.app()`
- Current note model: `app.currentNote`
- Input listener: title input event.
- Autosave: approximately one second after changes.

The application captures the Title value into its model and then persists the note.

The previous detector required a fresh `works` value and app-store corroboration.

The new detector must support:

- Positive: `yes`, `works`
- Negative: `no`
- Empty after 30 seconds: no audible response

## 9.1 Existing detector path discrepancy

The archived source/deployment reconciliation records:

`/usr/local/bin/nuxel-notes-works-detector`

However, another baseline log attempted:

`/usr/libexec/nuxel/notes-works-detector.py`

That path did not exist.

Resolve the path mismatch.

There must be one documented, executable, deployed watcher path.

Do not silently invoke an old missing filename.

## 9.2 Preflight before audio

The previous mission observed:

- Notes Title visible.
- Notes Title focused.
- Notes Title editable.
- AT-SPI connected.

But there were zero key/text input events reaching the WebView.

That meant the previous 30-second/three-play detector could not reliably distinguish the user's response from a broken input channel.

Before the first playback:

1. Confirm lockscreen is unlocked.
2. Confirm Notes is open.
3. Confirm Title field is focused.
4. Confirm display is awake.
5. Confirm touchscreen/keyboard interaction is possible.
6. Confirm the on-screen keyboard appears or the intended keyboard input source works.
7. Ask the owner to type a preflight word such as `ready`.
8. Verify that the live Title changes to `ready`.
9. Verify the Notes model captures the new value.
10. Verify the save succeeds after the normal autosave delay.
11. Preserve the preflight evidence.
12. Reset to an empty Title field and establish a fresh test baseline.

Do not start the audio loop until this input channel passes.

Do not fake the preflight by injecting text programmatically.

The owner must perform the actual typing.

## 9.3 Notes watcher

Build or repair a lightweight test watcher.

It must observe:

- Current active Notes application.
- Current active note ID.
- Actual Title field.
- Field focused state.
- Field editable state.
- Field visible state.
- Freshness relative to the current iteration.
- Current Title value.
- Corresponding application model/storage value.

Use AT-SPI or the Notes application's actual live model.

Set the correct session accessibility bus address before initializing the AT-SPI library.

The archived working session uses:

`/run/nuxel-wayland/at-spi/bus`

Do not assume the bus path without checking the live session.

Do not inspect unrelated note bodies or dump the complete Notes database.

Store only the necessary confirmation metadata.

## 9.4 Freshness and response classification

For each test iteration:

1. Capture baseline Title and note ID.
2. Record the test start time.
3. Play once.
4. Wait up to 30 seconds.
5. Detect a fresh input change.
6. Confirm the current active Title.
7. Wait for Notes autosave if applicable.
8. Corroborate the actual store only when available and relevant.
9. Record the result.

Do not accept an old `yes` or `works` from a previous note.

Do not accept text from the Notes body.

Do not accept a random UI string.

## 9.5 Reset for the next test

After recording `no`, or after a 30-second empty response:

- Preserve the result.
- Establish a fresh empty Title.
- Ensure it remains focused and editable.
- Confirm the screen stays awake.
- Start the next iteration only after the baseline is clean.

Use a dedicated PWNAGE-40000 test note or a safe fresh test note.

Do not modify or delete unrelated user notes.

---

# 10. SCREEN AND INPUT STABILITY DURING THE TEST SESSION

The previous PWNAGE-40000 run encountered screen blanking at:

`IDLE_SCREEN_OFF timeout_ms=300000`

The system set:

`/sys/class/backlight/panel/bl_power=4`

There was also an earlier problematic direct backlight manipulation that triggered I2C bus instability and eventually required reboot.

Do not repeat that mistake.

Requirements:

- Keep the screen visible during the human test session.
- Use a supported Nuxel/system idle inhibitor where available.
- Alternatively, temporarily change the normal Nuxel screen timeout using its supported configuration interface.
- Record the original value.
- Restore the original value after testing.
- Do not write directly to panel backlight or `bl_power` sysfs nodes merely to wake the display.
- Do not permanently leave screen timeout set to `never`.
- Do not break touchscreen functionality.
- Do not lock the screen during testing.

A single 30-second response window must be long enough for the owner to hear the sound and enter the response.

---

# 11. REAL-TIME PCM AND HARDWARE OBSERVABILITY

The previous test logs sometimes captured the ALSA state only after playback ended.

That left the PCM at:

`state=SETUP`

with a stationary pointer.

This is not enough to determine what happened during the actual short playback.

The asset is only about 0.366 seconds long.

The diagnostic must sample while the player is alive.

## 11.1 Concurrent one-play capture

For each test:

1. Record the current PCM state and hardware pointer.
2. Start one `pw-play` process.
3. While it is running, concurrently sample:
   - PipeWire sink.
   - Stream node.
   - Active links.
   - ALSA `hw_params`.
   - ALSA PCM status.
   - Hardware pointer.
   - ABOX trigger messages where available.
   - DAPM speaker/amp widgets.
4. Wait for `pw-play` to exit.
5. Record its exit status.
6. Confirm all processes exited.
7. Record the final PCM state.

Use sufficiently frequent polling to catch the approximately 0.366-second sample.

A short-interval Python monitor is acceptable.

Do not use `bc` because the archive's previous test runner encountered:

`bc: command not found`

Use the available Python, `awk`, or shell arithmetic.

## 11.2 Required evidence

During a successful playback attempt, seek evidence such as:

- PipeWire stream active.
- Stream linked to `alsa_output.hw_0_1`.
- RDMA1 PCM `state=RUNNING`.
- Actual `hw_ptr` advancement.
- 48000 Hz hardware parameters.
- ABOX RDMA1 trigger start and stop.
- Right AMP DAPM path active.
- Physical SPEAKER output path active.
- No errors.
- Player completes normally.

Do not confuse these with audible confirmation.

They locate the remaining failure.

---

# 12. ITERATIVE FIXING STRATEGY

The user has authorized you to make the necessary audio software and routing changes.

Do not stop at the first `READY` result.

Do not simply write a report saying the software pipeline works.

Continue fixing and testing.

## Phase A — Preserve current known-good state

- Reconnect over Wi-Fi SSH.
- Check current route state.
- Check current firmware readiness.
- Check current PCM state.
- Check current mixer values.
- Check current PipeWire sink and volume.
- Back up all affected files.
- Record existing volume and sound mode.
- Record the ABOX Sound Type.
- Create TODO and evidence directories.

Do not overwrite the latest live route with an older copy from the repository.

## Phase B — First targeted test: SPEAKER mode

- Verify `ABOX Sound Type` options.
- Capture previous value.
- Set `SPEAKER` / enum 1.
- Read it back.
- Revalidate the actual route.
- Confirm Right AMP → SPEAKER.
- Run one `nuxel-pow.mp3`.
- Wait 30 seconds.

If `yes`/`works` appears:

- Preserve this mode.
- Make it persistent.
- Extend readiness checks to verify the mode.

If `no` or blank:

- Record the negative result.
- Preserve the configuration for comparison.
- Move to the next controlled hypothesis.

## Phase C — Verify sound policy and volume

Inspect:

- Current sound mode.
- PipeWire sink mute.
- Sink volume.
- `pw-play` gain.
- AMP mute controls.
- Left/Right AMP PCM Gain.
- The bridge and sound-cue policy.

Temporarily use normal audible mode for the test if needed.

Start from the existing volume.

If no audible output:

- Increase PipeWire sink volume in the controlled progression.
- Use one POW and one 30-second response per level.
- Monitor PCM and DAPM during each play.
- Record the exact setting at which the owner first hears sound.

Do not jump to maximum volume.

Do not change AMP protection or thermal settings.

## Phase D — Verify speaker route and channel delivery

If the correct ABOX mode and volume do not produce sound:

- Re-examine ABOX Sound Type.
- Inspect all speaker-related mixer enumerations.
- Inspect Right AMP SPK route.
- Inspect the right amplifier PCM Source.
- Inspect ABOX SPKAMP mapping.
- Inspect output channel routing.
- Inspect DAPM graphs during playback.
- Inspect CS35L41 logs.
- Inspect speaker output enable and amplifier mute.
- Inspect any required codec state established by the original vendor configuration.

Change one meaningful group at a time.

Do not invent mixer controls.

Do not randomly turn every mixer switch ON.

Do not use arbitrary register writes.

Do not disable amplifier protection.

## Phase E — Keep iterating

The loop is:

```text
DIAGNOSE NEXT FAILURE
        |
        v
CHANGE ONE LOGICAL SETTING
        |
        v
READ BACK THE CHANGE
        |
        v
VERIFY ROUTE READINESS
        |
        v
ANNOUNCE TEST
        |
        v
PLAY nuxel-pow.mp3 ONCE
        |
        v
WAIT 30 SECONDS
        |
        v
READ NOTES: YES / WORKS / NO / EMPTY
        |
        +---- YES / WORKS ----> OWNER CONFIRMED
        |
        +---- NO / EMPTY -----> NEXT DIAGNOSTIC ITERATION
```

The validation session must stay alive between attempts.

Do not require the owner to restart the SSH session or rerun the entire mission after each test.

Do not play additional diagnostic tones during the owner's 30-second response period.

---

# 13. SPECIFIC DEFECTS ALREADY FIXED — DO NOT REINTRODUCE THEM

## 13.1 Wrong audio test backend

Old GStreamer `pulsesink` test path:

- Did not reliably post EOS.
- Was killed before stream linking completed.
- Produced no samples in Settings testing.

Corrected path:

`pw-play`

Preserve it.

## 13.2 Wrong volume control

The previous volume implementation selected:

`ABOX PCM ext Out Fade Start`

as the first writable ALSA control.

This has a 0..1 range and caused volume keys to jump between extremes.

The corrected implementation uses PipeWire volume control:

```bash
wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+
wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-
```

Preserve this behavior.

## 13.3 Wrong amplifier PCM gain

Cold-boot value 19 was associated with a silent state.

Current route now uses 12.

Preserve and verify 12.

## 13.4 Incorrect 44.1 kHz graph clock at boot

A staged bundle previously overwrote the correct 48 kHz graph configuration with 44.1 kHz.

This was fixed in repository, deployed config, and stage.

Do not reintroduce 44.1 kHz as the S10+ hardware sink rate.

The input MP3 is 44.1 kHz and PipeWire can resample it.

The hardware route must remain at 48 kHz.

## 13.5 Stale default sink

Cold boot could publish the static sink without a default node.

The current bridge selects the sink by stable name and reads it back.

Preserve this behavior.

## 13.6 Cold-boot DSP readiness

The route is now gated on:

- Calliope `MUB0`.
- Both CS35L41 DSP1 processors booted and running.
- Required route controls.
- PipeWire sink.
- Default sink.
- 48 kHz rate.
- Native PipeWire connection.

Do not replace this with an optimistic one-time status-file check.

---

# 14. NOTES DETECTOR IMPLEMENTATION REQUIREMENTS

Inspect:

`tools/s10plus/a33/notes-works-detector.py`

Current deployed path is recorded as:

`/usr/local/bin/nuxel-notes-works-detector`

Make the watcher support the new interaction protocol.

Suggested output states:

- `PREFLIGHT_READY`
- `PREFLIGHT_FAILED`
- `WAITING`
- `OWNER_YES`
- `OWNER_WORKS`
- `OWNER_NO`
- `OWNER_NO_RESPONSE`
- `INPUT_CHANNEL_BROKEN`
- `NOTES_UNAVAILABLE`
- `INVALID_RESPONSE`

The watcher must:

- Use a 30-second deadline per individual test.
- Use a monotonic clock for elapsed time.
- Accept `yes` and `works` as positive.
- Accept `no` as explicit negative.
- Treat an empty field after the full window as no audible response if preflight succeeded.
- Record live Title focus, visibility and editability.
- Detect a fresh change after the current test.
- Corroborate against Notes current model/storage.
- Use the actual deployed path.
- Keep the watcher alive through multiple iterations.
- Never create an artificial positive result.
- Never interpret an old title from a previous note as current confirmation.

Preserve only the necessary test metadata.

Do not log unrelated user notes.

---

# 15. REPAIR THE PERSISTENT ROUTE AFTER THE OWNER CONFIRMS SOUND

Once the owner confirms the working configuration:

Update the source implementation and actual deployed files.

Primary source:

`services/nuxel-s10/bin/nuxel-audio-route.sh`

Other relevant areas:

- `services/nuxel-s10/systemd/nuxel-audio-route.service`
- `services/nuxel-s10/systemd/nuxel-audio-route-retry.service`
- `services/nuxel-s10/systemd/nuxel-audio-route.timer`
- `services/nuxel-s10/bin/nuxel-abox-firmware-reload-boot.sh`
- `services/nuxel-bridge/src/hw_providers.py`
- `tools/s10plus/a33/nuxel-sound-cue.py`
- `services/nuxel-session/systemd/nuxel-boot-sound.service`
- Relevant PipeWire and WirePlumber configuration.
- `configs/nuxel/audio/audio.json`.

## 15.1 Add the confirmed speaker mode

If `ABOX Sound Type=SPEAKER` is the confirmed fix:

- Set it in the persistent route.
- Read it back.
- Add it to `route_controls_ready()`.
- Require it in `--check`.
- Log it in route state.
- Ensure it is reapplied after cold boot.
- Ensure the retry timer cannot revert it.

Do not leave the only working setting as a manual terminal command.

## 15.2 Add the confirmed speaker output checks

Readiness must verify:

- Correct ABOX Sound Type.
- Right AMP route to physical SPEAKER.
- Correct ABOX mapping.
- Correct amplifier gain.
- Correct unmuted state.
- Required DAPM path.
- PipeWire sink.
- 48 kHz rate.
- Default sink.

Do not mark the route APPLIED if any mandatory speaker-path control is missing.

## 15.3 Persistent volume policy

If the speaker only becomes audible above the previous 25% limit:

- Record the first confirmed audible level.
- Correct the effective PipeWire volume policy.
- Update the bridge and Settings clamps consistently.
- Keep a user-adjustable volume range.
- Ensure boot route restoration does not force an inaudibly low value.
- Ensure periodic route retries do not overwrite a deliberately quieter user setting.
- Preserve amplifier protection and DSP1 firmware.

The actual PipeWire sink is the important output level for this static sink.

Do not assume the ALSA softvol plugin protects the direct PipeWire `hw:0,1` route.

---

# 16. BOOT PERSISTENCE — ONLY AFTER MANUAL SPEAKER CONFIRMATION

Avoid additional unnecessary reboots during the diagnostic iteration process.

The current repository already has a working firmware reload/route readiness sequence.

Once the owner has confirmed sound:

1. Preserve the verified speaker settings.
2. Apply them persistently.
3. Validate the boot readiness gate.
4. Verify the startup sound is gated on the corrected speaker route.
5. Verify there is only one startup sound attempt per boot.
6. Preserve the 48 kHz graph.
7. Verify the sound policy and default volume.
8. Back up all files and settings.
9. Perform one normal reboot.
10. Reconnect over Wi-Fi SSH.
11. Verify ABOX and both amplifier DSPs.
12. Verify ABOX Sound Type.
13. Verify the right amplifier's speaker mapping.
14. Verify gain 12.
15. Verify the default PipeWire sink.
16. Verify the 48 kHz hardware rate.
17. Verify startup cue readiness and event log.

Then reopen the owner confirmation workflow.

The owner will unlock Notes, focus an empty Title field and perform one fresh post-boot test.

Play `nuxel-pow.mp3` once.

Wait 30 seconds.

Require a fresh `yes` or `works`.

A successful startup player exit code is not a substitute for post-boot human confirmation.

---

# 17. DEPLOYMENT AND SAFETY

The user authorizes necessary non-destructive software, route, mixer and service modifications required to obtain physical speaker output.

This includes:

- Correcting ALSA mixer state.
- Correcting supported ABOX enum values.
- Reconfiguring PipeWire and WirePlumber.
- Correcting route scripts and systemd ordering.
- Rebuilding userspace programs when required.
- Correcting bridge and Nuxel audio APIs.
- Adjusting normal PipeWire volume within controlled test steps.
- Safely restarting audio services where necessary.

However:

**TWRP reflash is not authorized or expected.**

Do not:

- Flash a TWRP backup.
- Reflash the ROM or rootfs partition.
- Replace the kernel.
- Flash a boot image.
- Modify bootloader settings.
- Repartition storage.
- Write to modem or EFS partitions.
- Disable amplifier thermal protection.
- Disable DSP1 protection.
- Write arbitrary hardware registers.
- Raise amplifier analog gain blindly.
- Force all mixer controls ON.

The previous live software route produced working hardware DMA and once produced audible sound. A TWRP reflash is not a rational first-line fix.

If you find new evidence that a kernel/firmware change is genuinely unavoidable, document the exact blocker and stop before flashing anything.

Before deployment:

- Back up every changed live file.
- Preserve source/stage/deployed parity.
- Validate systemd units.
- Verify config syntax.
- Deploy staged files.
- Verify SHA-256 hashes.
- Preserve Wi-Fi SSH.
- Keep a rollback path.

Do not overwrite unrelated changes.

---

# 18. FINAL ACCEPTANCE MATRIX

Use PASS / FAIL / BLOCKED / NOT TESTED.

| ID | Requirement | Evidence |
|---|---|---|
| BASE-01 | Current route inventory | Complete device evidence |
| BASE-02 | Existing live route preserved | Backup and hashes |
| MODE-01 | ABOX Sound Type | Live enum and verified readback |
| MODE-02 | SPEAKER mode experiment | Owner response after one test |
| AMP-01 | Left AMP PCM Gain | Verified 12 |
| AMP-02 | Right AMP PCM Gain | Verified 12 |
| AMP-03 | Both DSP1 processors | Booted and running |
| AMP-04 | Speaker amplifier unmuted | Verified readback |
| ROUTE-01 | ABOX RDMA1_EN | Verified ON |
| ROUTE-02 | SPKAMP mapping | RDMA1 |
| ROUTE-03 | Right AMP physical speaker route | Verified |
| ROUTE-04 | DAPM speaker path | Active during test |
| PCM-01 | PipeWire sink | Correct node exists |
| PCM-02 | Default output | Correct sink readback |
| PCM-03 | Runtime format | 48 kHz S16LE stereo |
| PCM-04 | Stream activity | RUNNING during playback |
| PCM-05 | Hardware pointer | Advances during playback |
| PCM-06 | Actual active links | Stream to intended speaker path |
| VOL-01 | Single attenuation stage | No double attenuation |
| VOL-02 | Volume testing | Controlled owner-supervised ramp |
| ASSET-01 | POW file | Valid deployed asset/hash |
| TEST-01 | One playback per iteration | Exactly one invocation |
| TEST-02 | Response window | Full 30 seconds |
| TEST-03 | Notes preflight | Actual typing verified |
| TEST-04 | Positive confirmation | Fresh `yes` or `works` |
| TEST-05 | Negative response | `no` or empty classified correctly |
| TEST-06 | Repeated iteration | Same session stays active |
| PERSIST-01 | Route source updated | Confirmed settings committed |
| PERSIST-02 | Readiness gate | Speaker mode included |
| PERSIST-03 | Boot initialization | Correct mode and route restored |
| BOOT-01 | Fresh reboot | Successful |
| BOOT-02 | Post-boot route | Correct readback |
| BOOT-03 | Post-boot playback | New audible confirmation |
| SAFE-01 | Amp protections | Preserved |
| SAFE-02 | Recovery and SSH | Preserved |
| SAFE-03 | TWRP reflash | Not performed |

---

# 19. EVIDENCE AND REPORTS

Create:

`docs/beta-finalization/live/PWNAGE-40000-TODO.md`

Update the existing mission report:

`docs/beta-finalization/live/PWNAGE-40000-REPORT.md`

Store new evidence under:

`docs/beta-finalization/live/evidence/pwnage-40000/`

Use a fresh run directory for this final speaker investigation.

Include:

- Live route inventory.
- Current ABOX Sound Type value.
- All enum choices.
- SPEAKER-mode experiment and readback.
- Left/right amplifier routing.
- DAPM state.
- Gain values.
- PipeWire default sink and volume.
- Runtime PCM observations.
- Hardware pointer capture.
- The exact playback command.
- Every one-play test number.
- Every 30-second response result.
- Notes preflight evidence.
- First successful human confirmation.
- Confirmed volume level.
- Persistent route changes.
- Post-boot route and mode.
- Fresh post-boot confirmation.

Never log unrelated note content.

Do not record exact private data beyond the confirmation metadata required for the test.

---

# 20. FINAL REPORT FORMAT

## 1. Root cause

Explain exactly which speaker-specific setting, route, volume or lifecycle condition prevented sound.

Give priority to the ABOX Sound Type experiment.

## 2. Current live speaker route

Document:

- ABOX mode.
- RDMA1.
- SPUS/SIFS1/UAIF1.
- SPKAMP mapping.
- Right AMP physical speaker endpoint.
- DSP1.
- Amplifier gain.
- PipeWire sink.
- Volume.

## 3. Test history

For every iteration, record:

| Test | Change | Volume | Playback result | PCM evidence | Notes response |
|---|---|---:|---|---|---|
| 1 | Initial SPEAKER test | ... | ... | ... | ... |
| 2 | ... | ... | ... | ... | ... |

## 4. Human confirmation

Record the first fresh `yes` or `works`.

That exact successful configuration becomes the known-good speaker configuration.

## 5. Persistent implementation

List all files and services changed.

## 6. Reboot verification

Report post-boot mode, route, PCM, sink, and fresh human confirmation.

## 7. Remaining issues

List any genuine unresolved hardware or audio problems.

## 8. Rollback

Provide exact backup and recovery paths.

---

# FINAL EXECUTION RULES

1. Do not restart the entire audio project.
2. Preserve the verified ABOX, CS35L41 and PipeWire work.
3. Investigate `ABOX Sound Type` first.
4. Do not overlook the possibility that VOICE mode is being used for a SPEAKER task.
5. Preserve the verified amplifier gain 12.
6. Verify Right AMP → physical SPEAKER.
7. Use one `nuxel-pow.mp3` playback per test.
8. Give the owner a full 30 seconds after each playback.
9. Accept fresh `yes` or `works` as positive.
10. Accept `no` or a full empty response as negative only after Notes input preflight passes.
11. Keep fixing after negative results.
12. Do not restart the SSH session between iterations.
13. Do not claim sound based on player success or DMA activity.
14. Do not stop at software readiness.
15. Do not TWRP reflash.
16. Do not flash the kernel or firmware.
17. Preserve all working recovery access.
18. Persist the first actually confirmed speaker configuration.
19. Reboot only after the working route is confirmed and persistent.
20. Require a fresh post-boot audible confirmation.

**THIS MISSION IS NOT COMPLETE UNTIL THE BUILT-IN S10+ SPEAKER MAKES THE NUXEL POW SOUND AND THE OWNER TYPES YES OR WORKS IN NOTES.**

No more READY-but-silent reports.

No more player-exited-successfully claims.

No more stopping at DMA evidence.

**KEEP ITERATING. FIX THE SPEAKER. WAIT 30 SECONDS. GET THE HUMAN CONFIRMATION.**

# PWNAGE-40000 — MAKE IT ACTUALLY POW. 🐧🔊
