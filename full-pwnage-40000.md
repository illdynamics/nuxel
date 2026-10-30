# FULL-PWNAGE-40000
# NUXEL S10+ — ULTIMATE AUDIO REPAIR, ROUTING, FIRMWARE READINESS AND BOOT PERSISTENCE

**Mission:** PWNAGE-40000  
**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte  
**OS:** Nuxel — custom Fedora-based ARM64 Linux  
**SSH transport:** Existing Wi-Fi SSH connection  
**SSH identity:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Primary playback asset:** `./assets/nuxel-pow.mp3`

---

# 0. MISSION OBJECTIVE

Finish the Nuxel audio system.

The objective is to make actual physical audio playback work reliably, persistently, and automatically after boot.

This is not a new audio architecture project. The repository already contains a substantial amount of S10+-specific audio work, and yesterday we heard actual test audio.

The latest human report is that:

- A 440 Hz tone was audible.
- Another diagnostic tone was audible.
- Multiple plays of `nuxel-pow.mp3` were audible.

Therefore, an actual hardware output path has worked.

The problem is to identify the successful live configuration, reconcile it with the repository, fix the remaining boot and routing problems, and make the working configuration persistent.

**Do not throw away the known-working path and start again with generic Linux audio instructions.**

Your mission is to inspect the running device, identify the actual state, implement the missing corrections, deploy safely, and prove audible playback.

## 0.1 Important evidence distinction

The uploaded repository contains older evidence, including `audio.md` dated 2026-10-29 20:12Z, which records that human audibility had not yet been confirmed at that point.

The user's later report that they heard the test tones and POWs is newer evidence and supersedes that older status.

Record the user's latest confirmation in the mission timeline. However, the exact output device and exact configuration used during the successful later test are not yet identified. Recover them from the live device, shell history, logs, and current service state.

Do not tell the user that audio has never worked.

Do not claim that every output route has worked merely because one route produced sound.

---

# 1. THE MOST IMPORTANT REPOSITORY FINDINGS

The following findings are based on inspection of the uploaded repository snapshot. Verify each one against the actual running handset before changing it.

## 1.1 Confirmed source/deployment mismatch: ABOX RDMA1_EN

Inspect:

`services/nuxel-s10/bin/nuxel-audio-route.sh`

The script currently contains a comment claiming:

> There is no 'ABOX RDMA0_EN' / 'ABOX RDMA1_EN' mixer control on this card.

It never sets `ABOX RDMA1_EN`.

However, the later live evidence file:

`docs/beta-finalization/live/evidence/pwnage-38000/live-audio-evidence-20261029b.txt`

records an actual control:

`ABOX RDMA1_EN`

The evidence identifies it as numid 1031 and shows it OFF during the silent test. The live correction included setting it ON and verifying the result.

This is the strongest confirmed source-level defect in the archive.

**Required action:**

- Re-query the actual control namespace on the live device.
- Confirm whether `ABOX RDMA1_EN` exists on the currently running card.
- Read its actual control type and allowed values.
- If present as in the previous evidence, ensure it is enabled as part of the persistent RDMA1 route.
- Verify the resulting value by control name.
- Update the checked-in route script.
- Remove the false comment.
- Update the relevant tests.
- Verify that every fresh boot applies this control before playback is declared ready.

Do not rely on numid 1031 as a permanent identifier. Use the real control name and verify it on the current card.

If the control does not exist on the actual running hardware revision, reconcile that discrepancy rather than forcing a guessed control.

Do not overwrite a live configuration that already has this control correctly enabled with the older checked-in script.

## 1.2 The S10+ uses a specific playback PCM

The evidence identifies:

- ALSA card: `beyond-madera`.
- Main codec path: live sysfs identifies `cs47l92-codec`.
- Two CS35L41 amplifier devices on I2C-11, addresses `0x40` and `0x41`.
- Known working playback path: RDMA1, device 1, normally `hw:0,1`.

The tested behavior:

- RDMA0 does not advance its hardware pointer.
- RDMA1 at 44.1 kHz produced `EIO` with the hardware pointer stuck at zero.
- RDMA1 at 48 kHz produced a running stream and advancing hardware pointer.
- Other tested RDMA devices returned backend-DAI errors.

Therefore:

**Do not route Nuxel's internal speaker playback to a generic `default` PCM without verifying what that default actually resolves to.**

Use the measured RDMA1 route and 48 kHz settings.

Discover the actual card name and current card index at runtime. The archived system uses card index 0, but do not assume that a card index can never change.

## 1.3 PipeWire static sink exists for a reason

Inspect:

`configs/s10plus/pipewire/50-nuxel-s10-alsa.conf`

The repository has a static PipeWire ALSA sink:

`alsa_output.hw_0_1`

with the S10+ RDMA1 device and 48 kHz format.

This was introduced because the image does not run the normal `systemd-udevd` path. WirePlumber's regular udev ALSA monitor therefore misses the MADERA card and can fall back to Dummy Output.

The static node bypasses that discovery dependency.

Preserve this approach unless live evidence proves that the architecture has changed.

Do not blindly enable `systemd-udevd` on the vendor 4.14 image. The existing project documents problems with its udev service and boot behavior.

For external USB Audio Class devices, add a carefully scoped hotplug solution if necessary rather than changing the whole udev architecture without testing.

## 1.4 PipeWire default-sink selection is not checked correctly

Inspect:

`services/nuxel-bridge/src/hw_providers.py`

The function `_ensure_default_sink()` selects:

`alsa_output.hw_0_1`

using `pactl set-default-sink`.

However, `_pipewire_play()` currently calls:

`self._ensure_default_sink()`

without checking whether it succeeded.

This creates an avoidable failure mode: the player can be started even though no valid default sink has been established.

Fix this.

Requirements:

- Verify the PipeWire socket is available.
- Verify the expected sink node exists.
- Set the default sink.
- Check the command result.
- Read back the actual default sink.
- Refuse to report playback success if routing is not established.
- Return an explicit error containing the real failure.
- Do not silently fall through to an unrelated output.

Also confirm that the actual stream is routed to the expected sink, not merely that the sink appears in `wpctl status`.

## 1.5 The correct S10+ ALSA hardware rate must remain 48 kHz

Inspect:

- `configs/s10plus/pipewire/50-nuxel-s10-alsa.conf`
- `services/nuxel-s10/pipewire/99-nuxel-s10.conf`
- `services/nuxel-s10/alsa/99-nuxel-s10-default.conf`
- `configs/s10plus/alsa/asound.conf`
- `configs/nuxel/audio/audio.json`

The repository documents that RDMA1 is the measured working PCM at 48 kHz.

There are older evidence snapshots that describe 44.1 kHz, while later evidence shows the corrected 48 kHz hardware stream.

Resolve this inconsistency using the actual live runtime state.

Do not merely grep a configuration file and call the sample rate correct.

During playback, inspect:

`/proc/asound/card0/pcm1p/sub0/hw_params`

and the corresponding status file.

Verify:

- `rate: 48000`.
- `state=RUNNING`.
- `hw_ptr` advances during actual playback.
- The ABOX playback trigger is activated.
- The stream closes cleanly.

Do not claim that the speaker is working solely because `pw-play` returns zero.

## 1.6 Two distinct DSP firmware systems must be checked

There are two separate firmware concerns.

### A. Samsung ABOX Calliope core firmware

The Samsung ABOX is probed early during boot, before the root filesystem is mounted.

The kernel's early `request_firmware_direct()` therefore fails to find the firmware under `/lib/firmware` or `/usr/lib/firmware`.

The repository records failures involving:

- `calliope_sram.bin`
- `calliope_sram_2.bin`
- `calliope_dram.bin`
- `calliope_dram_2.bin`

This can leave the Calliope core in `Invalid calliope state: 0`.

The relevant live readiness indicator is:

`/sys/devices/platform/18c50000.abox/calliope_version`

A valid ready state reports:

`MUB0`

The repository contains:

- `nuxel-abox-firmware-reload.sh`
- `nuxel-abox-firmware-reload-boot.sh`
- `nuxel-abox-firmware-reload.service`

The userspace workaround tries to force an ABOX runtime suspend/resume cycle after the root filesystem becomes available.

It can work manually when PipeWire and the Wayland session have released the PCM.

However, cold-boot loading has been unreliable.

Do not treat the reload script's exit code as proof that firmware loaded. The helper itself can exit zero while reporting that readiness is not confirmed. The boot wrapper attempts to verify `MUB0`, but the actual boot and retry lifecycle must still be validated.

### B. CS35L41 amplifier DSP1 protection firmware

The CS35L41 amplifiers have their own DSP firmware and preload requirements.

The archived investigation found that both protection DSPs had previously failed to boot and experienced mailbox timeouts.

The live correction included selecting the correct DSP1 firmware and enabling preload. Evidence then recorded both amplifier DSPs as booted and running, with the expected WMFW files loaded.

Verify both amplifier instances independently.

Inspect the real control namespace and verify:

- Correct DSP1 firmware selection.
- Preload switch state.
- Actual firmware file loaded.
- DSP booted.
- DSP running.
- No fresh mailbox timeout.

Do not confuse these CS35L41 DSPs with the ABOX Calliope core.

**Both firmware layers must be ready for a genuine internal speaker route.**

## 1.7 Boot-sound readiness is currently too weak

Inspect:

`services/nuxel-session/systemd/nuxel-boot-sound.service`

and:

`tools/s10plus/a33/nuxel-sound-cue.py`

The boot service currently uses the existence of:

`/run/nuxel-audio-route.state`

as a readiness condition.

However, the route script can record deferred state, and a file's existence is not proof that all mandatory controls have been configured.

The service also checks for:

`/usr/share/nuxel/assets/nuxel-boot-audio.mp3`

while `nuxel-sound-cue.py` actually uses:

`nuxel-pow.mp3`

Correct this mismatch.

The boot cue must only run after the actual audio route is ready.

A correct boot readiness gate must verify, as applicable:

- ABOX Calliope `MUB0`.
- Both CS35L41 DSP1 instances ready.
- RDMA1 routing controls read back correctly.
- `ABOX RDMA1_EN` enabled.
- Required ABOX crossbar and amplifier paths enabled.
- PipeWire running.
- Static RDMA1 sink present.
- Actual default sink equals the intended sink.
- The route state explicitly says APPLIED and includes successful readbacks.

Do not use a stale state file from a previous attempt.

The startup POW must not play against Dummy Output or an uninitialized ABOX.

## 1.8 Existing audio bridge and test path

The archive documents that the previous Settings → Test Audio path used GStreamer with `pulsesink`, then killed the player after a 2.5-second window.

On this device, that test path did not reliably establish a working stream.

The bridge was changed to use:

`pw-play --volume <gain> /usr/share/nuxel/assets/nuxel-pow.mp3`

This is the preferred current PipeWire path.

Preserve the `pw-play` implementation and remove any stale production references to the broken GStreamer test path unless a separately validated reason exists.

Do not use direct ALSA playback when PipeWire owns `hw:0,1`; the archived evidence records EBUSY behavior in that situation.

---

# 2. SSH ACCESS AND MISSION INITIALIZATION

Connect through the existing Wi-Fi SSH path using:

`~wicked/.ssh/wicked_wqn_id_rsa`

Example:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa nuxel@PHONE_IP
```

Use the existing known phone IP and account.

Do not guess the IP.

Do not expose or copy the private key.

Preserve SSH host-key verification.

Do not switch to USB or serial as a workaround.

If the key or network access fails, stop and report the exact failure.

## 2.1 Initial inventory

Record:

- OS release.
- Kernel version.
- Device model.
- ALSA cards.
- PCM devices.
- Mixer controls.
- Codec and amplifier sysfs devices.
- ABOX runtime-PM state.
- Calliope firmware version.
- CS35L41 DSP status.
- PipeWire and WirePlumber status.
- PipeWire socket.
- Available sinks.
- Current default sink.
- ALSA hardware parameters.
- Installed audio utilities.
- Relevant systemd units.
- Recent audio-related logs.

Use the real device state rather than trusting old evidence.

## 2.2 Create the TODO

Create:

`docs/beta-finalization/live/PWNAGE-40000-TODO.md`

Create the evidence directory:

`docs/beta-finalization/live/evidence/pwnage-40000/`

Record all work before changing files.

Every item must have:

- Diagnosis.
- Relevant source path.
- Current deployed path.
- Planned fix.
- Test.
- Result.
- Status: TODO / IN PROGRESS / BLOCKED / VERIFIED.

---

# 3. CRITICAL SAFETY: RECONCILE THE LIVE PHONE WITH THE REPOSITORY

Before deploying anything, compare the repository version with the running handset.

This is mandatory because the archive contains an older route script that contradicts later live evidence.

Compare:

- Repository route script.
- Deployed `/usr/lib/nuxel/nuxel-audio-route.sh`.
- Systemd unit files.
- PipeWire configuration.
- WirePlumber configuration.
- ALSA configuration.
- Audio asset location.
- Sound-cue script.
- Bridge audio provider.
- Audio settings frontend.
- ABOX reload scripts and services.
- Live mixer values.
- Live service state.

Use hashes and timestamps where useful.

Create a source/deployment reconciliation table.

**Never overwrite a working live setting with an older checked-in version simply because the repository contains it.**

If the handset currently contains a configuration that produced the audible POW, preserve it first.

Identify the exact source and setting differences, then bring the repository up to the verified live configuration.

Preserve uncommitted development work.

Back up all files before changing them.

---

# 4. RECONSTRUCT THE LAST KNOWN-WORKING PLAYBACK PATH

The user's newer report establishes that sound has been heard.

Find the most recent successful live experiment.

Inspect:

- Shell history.
- Current and previous logs.
- Mission evidence.
- `pw-play` invocation history.
- `aplay` invocation history.
- Audio bridge logs.
- ALSA mixer state.
- PipeWire node state.
- ABOX control state.
- DSP firmware state.
- Systemd journal.
- Temporary test scripts.
- Existing audio validation output.

Search for:

- `ABOX RDMA1_EN`
- `nuxel-pow.mp3`
- `pw-play`
- `hw:0,1`
- `48000`
- `MUB0`
- `abox_uaif_trigger`
- `abox_rdma_trigger`
- `CS35L41`
- `DSP1`
- `SPKAMP`
- `AMP PCM Gain`
- `PCM Source`
- `Sound Type`

The aim is to identify:

1. Which physical output produced the audible sound.
2. Which PCM was used.
3. Which sample rate was active.
4. Which amplifier/DSP path was selected.
5. Which crossbar controls were configured.
6. Whether the ABOX core firmware was loaded.
7. Whether CS35L41 protection firmware was running.
8. Which PipeWire sink was the default.
9. Which player was used.
10. Which settings were temporary and which were already persistent.

Do not reset controls before capturing the known-good state.

If the precise successful run cannot be reconstructed, state that clearly and use the archived working route evidence as the best starting point.

---

# 5. FIX THE PERSISTENT ABOX PLAYBACK ROUTE

## 5.1 Correct the missing RDMA1 enable

The checked-in route script explicitly denies the existence of `ABOX RDMA1_EN`.

Later live evidence demonstrates that this control existed and was OFF.

This must be resolved first in the persistent route implementation.

Use the current ALSA card's actual control namespace.

Inspect the control type, values, and allowed choices.

If the control exists as in the previous live evidence:

- Set it to the correct enabled state.
- Read it back.
- Record its verified state.
- Ensure it is configured on every boot.
- Ensure route readiness fails if this mandatory control cannot be set.

Do not hardcode the archived numid.

Do not trust the current script's comment.

Do not pretend the route is applied if RDMA1 remains disabled.

## 5.2 Preserve the rest of the proven ABOX route

Inspect and verify the route controls, including:

- `ABOX SPUS IN1`
- `ABOX SPUS OUT1`
- `ABOX SIFS1`
- `ABOX UAIF1 SPK`
- `ABOX SIFS1 OUT Switch`
- `ABOX UAIF1 Switch`
- `ABOX RDMA1_EN`

Also inspect:

- `ABOX SPKAMP_EN`
- `ABOX SPKAMP_A`
- `ABOX SPKAMP_B`
- Left and Right AMP enable controls.
- Left and Right PCM Source.
- ABOX Sound Type.
- Relevant CS35L41 amplifier playback and mute controls.

The archive's later live correction records:

- Left/Right PCM Source set to ASP.
- ABOX Sound Type set to 0.
- SPKAMP routing assigned to RDMA1.
- Left/Right AMP enable.
- PipeWire default sink `alsa_output.hw_0_1`.

The evidence also contains different observed PCM Gain values in different captures. One later status reports gain 12; another capture shows 19.

Therefore:

**Do not blindly hardcode a historical AMP PCM Gain value.**

Read the actual control range and current value. Use measured, safe adjustments only if necessary.

Do not set every mixer switch to maximum or unmute unrelated controls.

## 5.3 Fix the route script's state handling

Inspect:

`services/nuxel-s10/bin/nuxel-audio-route.sh`

The existing script has several paths where a failed mandatory mixer operation can exit with status zero.

It can also write a route-state file whose mere existence does not prove that all necessary controls were successfully configured.

Repair this behavior.

Requirements:

- Identify all mandatory controls.
- Execute bounded operations.
- Read back each mandatory value.
- Record each actual result.
- Record `state=deferred` when hardware is not ready.
- Record `state=failed` when a mandatory control cannot be applied.
- Record `state=applied` only after every mandatory control passes readback.
- Include device/card identity, route name, and readiness details.
- Remove stale state before starting a new application attempt.
- Never leave a previous `applied` state visible after a failed retry.
- Ensure a deferred retry does not leave orphaned mixer processes in D-state.
- Keep boot non-blocking and bounded.

A service returning zero is not sufficient if the actual route failed.

## 5.4 Preserve the real codec identity

The live evidence identifies:

`cs47l92-codec`

Some documentation refers to CS47L93.

Use the actual live sysfs, ALSA and driver information as truth.

Reconcile stale references.

Do not choose a generic codec profile based on a stale model name.

## 5.5 UCM profile

Inspect:

`configs/s10plus/alsa-ucm/SamsungBeyond2/HiFi.conf`

The current profile is deliberately a stub with empty enable/disable sequences.

Do not invent codec mixer controls or copy a generic Samsung profile.

If UCM is required:

- Capture real controls.
- Derive sequences from the actual current hardware.
- Back up the prior profile.
- Validate every generated control name.
- Install only after tests.
- Roll back if the new profile breaks the known-good route.

The route must be verified through real mixer values and actual hardware operation, not merely by the presence of a UCM file.

---

# 6. FIX AND VERIFY BOTH DSP FIRMWARE LAYERS

## 6.1 ABOX Calliope core

The initial kernel probe occurs before the root filesystem is mounted.

The four relevant core blobs are:

- `calliope_sram.bin`
- `calliope_sram_2.bin`
- `calliope_dram.bin`
- `calliope_dram_2.bin`

Verify all required files exist in the actual deployed firmware directory.

Inspect:

- `/sys/devices/platform/18c50000.abox/power/control`
- `/sys/devices/platform/18c50000.abox/power/runtime_status`
- `/sys/devices/platform/18c50000.abox/calliope_version`
- `dmesg`
- ABOX systemd units.
- The actual kernel firmware-loading messages.

The readiness condition is the actual Calliope version:

`MUB0`

Do not accept:

- A successful shell command.
- An exit code of zero.
- A runtime-PM status of active.
- An ABOX device directory existing.

None of these alone proves that the Calliope core firmware was loaded.

## 6.2 Audit the userspace reload sequence

Inspect:

- `services/nuxel-s10/bin/nuxel-abox-firmware-reload.sh`
- `services/nuxel-s10/bin/nuxel-abox-firmware-reload-boot.sh`
- `services/nuxel-s10/systemd/nuxel-abox-firmware-reload.service`

The current design stops Wayland/PipeWire and the audio route before attempting a PM cycle, because active audio components can hold a runtime-PM reference.

Verify that the actual service:

- Stops the right services.
- Waits for PipeWire to release the device.
- Performs a valid PM cycle.
- Waits for the real firmware response.
- Retries a bounded number of times.
- Rechecks `MUB0`.
- Restores the audio session on success and failure.
- Does not leave Wayland stopped.
- Does not create an ordering loop or repeated service restart.
- Does not report readiness when the firmware is missing.

Review the systemd transaction and journal, not only the shell script.

The service is currently associated with the Wayland startup lifecycle and stops/restarts that session as part of its work. Verify that behavior on the actual system and simplify it safely if possible.

Do not create a boot-time deadlock.

## 6.3 Kernel firmware embedding is outside current authorization

The archive suggests that embedding the four Calliope blobs with `CONFIG_EXTRA_FIRMWARE` could solve the rootfs-too-late problem at its true source.

However, this requires a kernel build and potentially replacing/flashing a boot image.

**Do not build and flash or replace the kernel as part of this mission without separate explicit authorization.**

Do not alter the bootloader, firmware partitions, DTB, or boot image.

First pursue and validate the existing safe userspace workaround.

If the only reliable solution is a kernel-level firmware-loading change:

- Document the exact reason.
- Provide the required firmware list and configuration proposal.
- Explain why userspace cannot guarantee cold-boot readiness.
- Mark it `BLOCKED_KERNEL_AUTHORIZATION`.
- Leave the running kernel untouched.

## 6.4 CS35L41 DSP1 protection firmware

Independently verify both amplifier DSPs.

The archived fix used the appropriate DSP1 firmware selection and preload switch.

Check:

- Correct DSP1 firmware enum.
- Preload switch.
- Firmware file availability.
- Firmware load messages.
- DSP booted state.
- DSP running state.
- Mailbox errors.

Both left and right amplifier DSPs must be ready.

Do not confuse a CS35L41 DSP firmware success with Calliope `MUB0`.

They are separate readiness requirements.

---

# 7. VERIFY THE ACTUAL 48 KHZ RDMA1 PLAYBACK PATH

The known device-specific path is:

`RDMA1 → ABOX SPUS → SIFS1 → UAIF1 → CS35L41 amplifiers`

Expected PCM:

`hw:0,1`

Expected hardware rate:

`48000 Hz`

## 7.1 PipeWire configuration

Preserve and inspect:

- `configs/s10plus/pipewire/50-nuxel-s10-alsa.conf`
- `services/nuxel-s10/pipewire/99-nuxel-s10.conf`
- `services/nuxel-s10/wireplumber/99-nuxel-s10.conf`

The static ALSA node exists because normal udev discovery is unavailable on this image.

Verify:

- The static sink is created.
- The node name is `alsa_output.hw_0_1` or the validated current equivalent.
- The node points to RDMA1.
- The node has the intended 48 kHz clock.
- The actual default sink is that node.
- The PipeWire graph is not silently using Dummy Output.

## 7.2 Runtime verification

During every diagnostic playback, verify:

- Actual PipeWire default sink.
- Actual stream route.
- Active ALSA PCM.
- `hw_params` reports 48 kHz.
- PCM status reports RUNNING.
- `hw_ptr` advances.
- ABOX playback trigger occurs.
- No new `Invalid calliope state: 0`.
- No RDMA errors.
- No CS35L41 mailbox timeouts.
- PCM returns to idle cleanly after playback.

Do not mark the route as ready based on static configuration alone.

Do not use RDMA0 or another PCM as a random guess.

Only explore alternate RDMA paths if current live evidence proves the original RDMA1 path cannot be recovered.

---

# 8. PIPEWIRE PLAYBACK AND BRIDGE REPAIR

## 8.1 Use one consistent playback backend

PipeWire owns the current internal speaker PCM during normal operation.

Direct ALSA playback can therefore fail with EBUSY.

Use `pw-play` through the intended PipeWire sink for the normal Nuxel audio path.

Do not use the old GStreamer `pulsesink` test implementation as the main Test Audio path. The archived evidence shows it failed to produce a stream during the bounded test window.

Do not fall back to direct `nuxel-mp3-play` while PipeWire owns the device.

## 8.2 Fix default-sink validation

In `services/nuxel-bridge/src/hw_providers.py`:

- Check the return value of `_ensure_default_sink()`.
- Verify the requested sink exists.
- Verify PipeWire is actually available.
- Verify the selected default after the change.
- Return a proper failure if routing cannot be established.
- Never start `pw-play` on an unknown default route and report success.

Use a stable node name rather than a transient numeric sink ID.

## 8.3 Honest playback result

A successful `pw-play` exit code means that the player completed.

It does not mean that a human heard sound.

Expose this distinction in the bridge.

The bridge may report:

- Player launched.
- Stream completed.
- Sink selected.
- PCM active.
- Hardware pointer advanced.
- DSP ready.
- Audible confirmation pending.

Only the Notes handshake or another validated human confirmation can establish audible success.

---

# 9. HUMAN-IN-THE-LOOP NOTES CONFIRMATION

This is mandatory.

## 9.1 The agreed workflow

The user will:

1. Unlock the phone.
2. Open Nuxel Notes.
3. Focus the empty Title field.
4. Leave Notes visible.

After a manual test batch is played, the user will type:

`works`

into the Title field if the POW sound was audible.

The agent must detect the new value.

## 9.2 The archive contains an existing detection opportunity

Inspect:

`pwa/nuxel-apps/notes/js/notes.js`

The source contains:

- Title input ID: `note-title`.
- Notes store key: `nuxel-notes`.
- An application interface exposed as `window.nuxelNotes`.
- A current application model available through `window.nuxelNotes.app()`.

The Notes application captures title input into the current note model and persists it through its storage mechanism.

Inspect the complete source and determine the live storage/backend implementation.

Use the least invasive method to observe only the current active note's title.

Possible mechanisms:

- Live Notes application model.
- Existing Nuxel storage bridge.
- Current note record in the Notes storage model.
- Live screenshot/accessibility capture as a fallback.

Do not assume that SSH directly exposes the graphical screen.

Do not read unrelated note contents.

Do not transmit or dump the entire Notes database.

## 9.3 Validate the observer

Before starting audio tests:

1. Confirm the Notes app is open.
2. Identify the active note.
3. Confirm that its current title is empty.
4. Record a baseline of the active note ID/state.
5. Determine how to detect a new title value.
6. Validate that the watcher sees a title-field change rather than an old saved note.
7. Ensure the observer remains alive through multiple audio test batches.

The exact word `works` must appear in the currently active note title after the current test.

A stale `works` in another note is not a confirmation.

A screenshot captured before the test is not a confirmation.

A text string somewhere else in the UI is not a confirmation.

## 9.4 Exactly three plays per manual batch

Every manual confirmation test must play the exact asset:

`./assets/nuxel-pow.mp3`

three times sequentially.

The playback mechanism must wait for each invocation to finish.

```text
MANUAL TEST BATCH
       |
       v
PLAY nuxel-pow.mp3 — 1
       |
       v
WAIT FOR COMPLETION
       |
       v
PLAY nuxel-pow.mp3 — 2
       |
       v
WAIT FOR COMPLETION
       |
       v
PLAY nuxel-pow.mp3 — 3
       |
       v
WAIT FOR COMPLETION
       |
       v
WAIT FOR NOTES CONFIRMATION
       |
       +---- NEW TITLE = works ----> RECORD PASS
       |
       +---- NO CONFIRMATION ------> DIAGNOSE AND FIX
                                      |
                                      v
                                  NEXT BATCH
```

The agent must:

- Play exactly three times per batch.
- Never overlap players.
- Never create a playback backlog.
- Never play extra diagnostic tones during the batch.
- Never play additional boot or volume feedback sounds during the batch.
- Wait until the batch has finished before waiting for `works`.
- Record the active output route and configuration.
- Keep the same validation session running between batches.

Do not replace the three separate plays with a previously generated combined three-burst WAV. The agreement is three plays of the actual supplied MP3 asset.

## 9.5 Confirmation watcher

Build or reuse a persistent watcher if necessary.

Suggested directory:

`scripts/audio-validation/pwnage-40000/`

Suggested outputs:

- `session.json`
- `batches.jsonl`
- `current-route.json`
- `notes-confirmation.json`
- Diagnostic logs.

Keep the watcher lightweight and event-driven where possible.

If polling is necessary, use a modest interval and stop polling when there is no active test batch.

Record:

- Batch number.
- Output route.
- Start time.
- Three individual playback results.
- Hardware state.
- Notes active note identifier.
- Previous title.
- New title.
- Confirmation timestamp.
- PASS/FAIL.

When `works` is detected:

- Record PASS.
- Do not clear the title.
- Do not overwrite the note.
- Do not keep testing that same route unnecessarily.
- Preserve the configuration that produced the audible result.

If the agent cannot establish a reliable Notes-state observer, it must report that and request a clearly explained fallback. It must never fake a detection.

## 9.6 Reboot behavior

A reboot will close Notes.

Before rebooting:

- Save the current mission and test state.
- Record every confirmed route.
- Tell the user that Notes must be reopened.
- After boot, reconnect over Wi-Fi SSH.
- Ask the user to unlock the phone and refocus an empty Title field.
- Re-establish the watcher without discarding earlier results.
- Resume the same mission rather than restarting from scratch.

---

# 10. INTERNAL SPEAKER FIRST

The internal speaker is the primary route.

Do not spend the initial test cycles on Bluetooth or HDMI.

First recover the known RDMA1-to-amplifier path.

Verify the following in sequence:

1. Calliope `MUB0`.
2. CS35L41 left DSP1 booted/running.
3. CS35L41 right DSP1 booted/running.
4. `ABOX RDMA1_EN` enabled.
5. RDMA1 selected as the intended source.
6. ABOX crossbar path correct.
7. SPKAMP routing correct.
8. Amplifier enables correct.
9. PipeWire static sink present.
10. PipeWire default sink selected.
11. 48 kHz hardware PCM parameters.
12. PCM actually running with advancing hardware pointer.

Then run one three-POW confirmation batch.

If the user does not enter `works`:

- Preserve the complete current evidence.
- Identify the earliest failing layer.
- Change one logically related set of controls.
- Validate the change.
- Run the next three-POW batch.

Do not randomly change multiple amplifier, DAPM and crossbar values at once.

Once audible:

- Record the exact configuration.
- Preserve it.
- Update the source implementation.
- Reapply it from the persistent service.
- Verify a service restart does not break the sound.

---

# 11. SAFE GAIN STAGING AND VOLUME

Inspect:

`configs/nuxel/audio/audio.json`

The repository establishes a safe-volume policy, including a maximum intended output ceiling of 25%.

Respect that limit.

Do not increase the physical output beyond the existing safe cap.

Important technical detail:

The static PipeWire hardware sink can bypass the ALSA `softvol` plugin configuration. Therefore an ALSA softvol ceiling alone does not guarantee a safe PipeWire sink level.

Enforce and verify the real PipeWire sink limit.

Requirements:

- Keep sink volume within the 25% ceiling.
- Use a low initial test level.
- Respect the user-selected volume.
- Do not silently increase gain to maximum.
- Do not change amplifier gain controls blindly.
- Read their actual ranges and enumerated values.
- Do not assume an old PCM Gain value applies to the current driver state.
- Record all gain changes.

The asset is short and already exists:

`assets/nuxel-pow.mp3`

The archived evidence records successful decoding and 48 kHz stereo output.

Verify the current asset checksum and deployed copy.

Do not convert or replace it unless a genuine decoding problem is found.

---

# 12. PERSISTENT AUDIO SERVICE DESIGN

## 12.1 Required boot sequence

The ideal boot sequence is:

```text
KERNEL AND ROOTFS INITIALIZE
              |
              v
AUDIO HARDWARE DISCOVERED
              |
              v
CALLIOPE FIRMWARE READY
              |
              v
MUB0 VERIFIED
              |
              v
CS35L41 DSP1 FIRMWARE VERIFIED
              |
              v
RDMA1 ROUTE APPLIED
              |
              v
MANDATORY CONTROL READBACKS PASS
              |
              v
PIPEWIRE AND WIREPLUMBER READY
              |
              v
STATIC RDMA1 SINK AVAILABLE
              |
              v
DEFAULT SINK VERIFIED
              |
              v
Nuxel UI / LOCKSCREEN READY
              |
              v
SINGLE STARTUP POW
```

The actual systemd dependency graph may differ, but it must produce the same readiness guarantees.

Do not create circular dependencies.

Do not make the UI wait indefinitely for audio.

Do not let a failed optional audio route block the entire phone boot.

## 12.2 Repair route-state semantics

The current state file:

`/run/nuxel-audio-route.state`

must represent real readiness.

Do not write `state=applied` before mandatory route controls have passed readback.

Use explicit states such as:

- `absent`
- `deferred`
- `firmware_not_ready`
- `route_failed`
- `applied`

Include evidence for each mandatory control.

The boot-sound service must not merely check whether the state file exists.

It must check whether it contains the current boot's valid applied state.

Do not accept a stale file from an earlier boot.

## 12.3 Repair startup sound asset condition

The systemd unit currently checks for `nuxel-boot-audio.mp3`, while the sound-cue script uses `nuxel-pow.mp3`.

Make the asset checks consistent.

Verify:

- Deployed path.
- File permissions.
- Checksum.
- Decoder support.
- Player location.
- PipeWire runtime path.

Do not make startup audio dependent on the current shell directory.

## 12.4 Startup POW behavior

After the audio route genuinely becomes ready:

- Play `nuxel-pow.mp3` once.
- Use the existing sound-cue mechanism or a correctly integrated replacement.
- Respect silent/vibration mode.
- Respect the safe gain cap.
- Do not hold the critical boot path hostage.
- Do not replay after every service restart.
- Do not play repeatedly if readiness polling runs again.
- Do not overlap manual confirmation tests.

The cue currently uses a once-per-boot attempted marker. Inspect its behavior carefully.

Do not permanently record a successful boot sound merely because the player was attempted.

Record attempted, player-completed and human-confirmed as different states.

A player completion is not an audible confirmation.

The startup sound must happen after `MUB0`, CS35L41 readiness, the RDMA1 route, and the default PipeWire sink have been verified.

---

# 13. AUDIO SETTINGS AND TEST AUDIO

Inspect:

- `services/nuxel-bridge/src/hw_providers.py`
- `pwa/nuxel-apps/settings/hardware-settings.js`
- The related Settings HTML/UI.
- Bridge audio API handlers.

The earlier Test Audio implementation used GStreamer `pulsesink` and did not reliably create a real hardware stream before the timeout.

The updated bridge uses PipeWire `pw-play`.

Preserve the known-good backend.

Fix default sink error handling as described above.

## 13.1 Test Audio button

The Settings application must have a working Test Audio button.

It must:

1. Use the currently selected output route.
2. Use the deployed `nuxel-pow.mp3`.
3. Run the same exact three-play manual test batch.
4. Report actual backend and route status.
5. Never claim that the owner heard the sound without confirmation.
6. Prevent overlapping tests.
7. Wait for user confirmation.

Show useful states:

- Audio system starting.
- Output unavailable.
- Route ready.
- Playing test batch.
- Waiting for confirmation.
- Audible confirmation received.
- Playback failed.
- Hardware route blocked.

Do not use a fake success indicator.

## 13.2 Audio state

The UI must distinguish:

- Audio service available.
- Output device present.
- Output selected.
- Stream completed.
- Physical audibility confirmed.

Do not represent one as another.

---

# 14. VOLUME FEEDBACK

Preserve the existing working volume-control improvements.

The archive records a previous defect where the volume handler selected:

`ABOX PCM ext Out Fade Start`

as the first writable control. That control has a 0..1 range and caused volume keys to jump between extremes.

The later correction uses the PipeWire default sink:

```bash
wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+
wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-
```

Preserve the measured 5% step behavior.

The user wants `nuxel-pow.mp3` as volume feedback.

Requirements:

- Play the asset only after a genuine volume change.
- Use the selected PipeWire output.
- Respect mute and sound mode.
- Do not alter the user's configured volume.
- Do not force full volume.
- Coalesce rapid volume-key events.
- Avoid overlapping players.
- Avoid creating a backlog.
- Preserve responsive volume changes.

The archive contains existing throttling/locking work in the sound-cue script and button handling.

Inspect and preserve it rather than creating a parallel sound system.

During a manual confirmation batch:

- Suppress volume-feedback POWs.
- Suppress duplicate boot cues.
- Suppress unrelated test tones.
- Allow only the three requested asset plays.

---

# 15. EXTERNAL AUDIO ROUTES

After the internal speaker is confirmed and persistent, inspect other available outputs.

Do not let optional routes destabilize the primary route.

## 15.1 3.5 mm wired headphones

The archive reports a headphone jack path but no physical accessory was inserted during the earlier test.

Check actual jack detection and route controls.

When connected:

- Detect the route.
- Select the correct hardware path.
- Verify audio output.
- Switch back when unplugged.

A headphone PCM or codec output existing in ALSA does not prove a physical headphone path works.

Use a separate three-POW Notes confirmation batch.

## 15.2 Bluetooth audio

The archive shows BlueZ active but no paired/connected audio device in the earlier test.

Do not confuse Bluetooth connectivity with Bluetooth audio.

Verify:

- A paired and connected device.
- Audio profile.
- PipeWire BlueZ node.
- Selected sink.
- Stream routing.
- Actual playback.

Preserve existing pairings.

Do not introduce unnecessary re-pairing.

Use a three-POW confirmation batch when an audio device is connected.

## 15.3 USB-C active DAC / USB Audio Class

The kernel configuration enables USB Audio Class support, but the archive did not show a UAC card physically connected.

Normal udev-based hotplug discovery is unavailable on this image.

A safe solution may require a dedicated userspace monitor that observes actual device/card appearance and exposes a PipeWire sink.

Do not blindly unmask `systemd-udevd`.

Do not confuse an active USB DAC with a passive analog adapter.

Do not claim support without connecting and testing an actual adapter.

The S10+ USB-C role and existing USB console/gadget use may conflict with USB host audio. Preserve the recovery console and inspect the current Type-C role before changing it.

Do not change USB role or disable an existing recovery path without a safe restoration plan.

## 15.4 USB-C passive analog adapter

A passive adapter is not the same as a USB Audio Class DAC.

Inspect the hardware accessory and actual codec routing.

Do not assume that a USB DAC result proves passive analog compatibility.

Test separately if the required physical adapter is available.

## 15.5 USB-C HDMI / DisplayPort audio

The archive reports:

- `CONFIG_DRM` is unset.
- `/sys/class/drm` is absent.
- The current display path uses framebuffer.
- An ALSA DP Audio PCM appears, but there is no working DRM/DP audio path.

This suggests that genuine DP/HDMI audio is blocked by the current kernel/display stack.

Do not claim that a present PCM device makes HDMI audio operational.

Do not attempt a kernel replacement or firmware flash under this mission.

Mark HDMI/DP audio `BLOCKED_KERNEL` unless the live system shows a newly available, real endpoint that can be tested safely.

---

# 16. AUDIO DIAGNOSTICS AND ACCEPTANCE

Use the existing device diagnostic architecture:

`tools/s10plus/a33/nuxel-audio-diag.sh`

Inspect its current commands and behavior before extending it.

It already supports a staged pipeline approach:

1. Card.
2. PCM.
3. Controls.
4. DAPM.
5. Route.
6. Actual PCM running.

Preserve the important rule that writable controls and DAPM widgets being ON are not proof of physical sound.

The diagnostic should identify the first broken stage and report its real evidence.

Do not make `nuxelctl audio status` report an unqualified OK when the speaker has not been confirmed.

---

# 17. REQUIRED TEST SEQUENCE

## Phase A — Recover and persist the internal speaker

- Reconcile live/repository settings.
- Fix RDMA1_EN.
- Verify ABOX Calliope readiness.
- Verify both CS35L41 DSP1 instances.
- Verify the rest of the speaker route.
- Verify PipeWire default sink.
- Verify 48 kHz.
- Perform the Notes-confirmed three-POW test.
- Preserve the working configuration.

## Phase B — Process and service persistence

Verify sound after:

- The manual test process exits.
- The bridge request ends.
- Nuxel UI restarts.
- Audio route service restarts.
- PipeWire/WirePlumber restart through a controlled test.

The audio must not depend on a foreground terminal or the temporary validation runner.

## Phase C — Boot persistence

Once the route is working and persistent:

1. Save the validated configuration.
2. Confirm service enablement and dependencies.
3. Confirm boot readiness gates.
4. Confirm that startup POW is configured to run only once.
5. Perform a normal reboot.
6. Allow Wi-Fi SSH to disconnect.
7. Reconnect using the specified key.
8. Verify `MUB0`.
9. Verify both CS35L41 DSPs.
10. Verify `ABOX RDMA1_EN`.
11. Verify route-state readbacks.
12. Verify PipeWire default sink.
13. Verify 48 kHz hardware parameters.
14. Verify the startup cue was attempted only after readiness.
15. Have the user reopen Notes with an empty focused Title field.
16. Run a fresh three-play batch.
17. Wait for the new `works` value.

Do not claim persistence based only on service enablement.

## Phase D — Other output routes

Test each physically available route independently.

Every physically tested route requires its own confirmation.

Do not claim that the internal speaker confirmation proves Bluetooth, wired headphones, USB DAC, or HDMI audio.

---

# 18. SAFETY, ROLLBACK AND RESOURCE USE

Before every deployment:

- Back up the existing source and live configuration.
- Preserve current working mixer values.
- Preserve the known-good default sink.
- Preserve the existing audio service definitions.
- Review exact changed files.
- Validate service syntax.
- Validate shell and Python code.
- Test route logic with readbacks.
- Maintain Wi-Fi SSH.
- Provide rollback.

Do not:

- Flash firmware.
- Replace or flash the kernel.
- Change the bootloader.
- Modify device-tree or boot partitions.
- Repartition storage.
- Force all mixer controls to maximum.
- Unmute unrelated paths.
- Re-enable udev indiscriminately.
- Remove Bluetooth pairings.
- Break USB console/recovery.
- Leave long-running test processes.
- Create permanent high-frequency polling.
- Introduce repeated audio playback loops.

If the only complete fix requires kernel-level firmware embedding, document it and request separate authorization.

Audio must not create a battery-draining background service or make Nuxel less responsive.

---

# 19. ACCEPTANCE TEST MATRIX

Use PASS / FAIL / BLOCKED / NOT TESTED.

A PASS requires the stated evidence.

| ID | Test | Required evidence |
|---|---|---|
| SOURCE-01 | Live/source route reconciliation | Hashes and difference report |
| ROUTE-01 | ABOX RDMA1_EN | Correct real control value |
| ROUTE-02 | ABOX SPUS/SIFS1/UAIF1 route | Readback of each mandatory control |
| ROUTE-03 | SPKAMP routing | Correct verified routing |
| ROUTE-04 | AMP enable and mute | Actual current values |
| ROUTE-05 | PCM Source / Sound Type | Verified route values |
| DSP-01 | Calliope firmware | `MUB0` |
| DSP-02 | CS35L41 left DSP1 | Firmware loaded, booted and running |
| DSP-03 | CS35L41 right DSP1 | Firmware loaded, booted and running |
| PCM-01 | RDMA1 | Correct PCM selected |
| PCM-02 | Sample rate | Actual 48000 Hz |
| PCM-03 | Hardware pointer | Advances during playback |
| PCM-04 | ABOX trigger | Real playback trigger evidence |
| PW-01 | PipeWire sink | Expected static sink exists |
| PW-02 | Default sink | Readback confirms correct sink |
| PW-03 | Playback backend | `pw-play` completes through intended sink |
| PW-04 | Failed sink selection | Correct failure, no false success |
| SPEAKER-01 | Internal speaker | Fresh Notes `works` confirmation |
| LIFE-01 | Test process exit | Audio remains functional |
| LIFE-02 | UI restart | Audio remains functional |
| LIFE-03 | Audio service restart | Audio recovers |
| BOOT-01 | ABOX cold-boot readiness | `MUB0` after reboot |
| BOOT-02 | Route after boot | Mandatory controls verified |
| BOOT-03 | Startup POW | Single correctly gated attempt |
| BOOT-04 | Post-boot audible test | Fresh Notes `works` confirmation |
| SET-01 | Test Audio button | Three real POW plays |
| VOL-01 | Volume control | Correct 5% increments |
| VOL-02 | Volume feedback | No overlaps or backlog |
| OUT-01 | Wired headphones | Physical test and confirmation, if available |
| OUT-02 | Bluetooth audio | Physical test and confirmation, if available |
| OUT-03 | Active USB DAC | Physical test and confirmation, if available |
| OUT-04 | Passive USB-C analog | Physical test and confirmation, if available |
| OUT-05 | HDMI/DP | Real endpoint and physical test, or documented kernel blocker |
| SAFE-01 | Volume ceiling | Actual PipeWire sink stays within 25% |
| SAFE-02 | Resource use | No runaway playback or polling |

---

# 20. REQUIRED EVIDENCE

Use:

`docs/beta-finalization/live/evidence/pwnage-40000/`

Capture:

- Initial device and kernel inventory.
- Actual ALSA card and PCM inventory.
- Actual mixer control namespace.
- Current route readbacks.
- ABOX Calliope status.
- Firmware load errors and recovery.
- Both CS35L41 DSP status reports.
- PipeWire sink and default-sink readback.
- ALSA `hw_params` and PCM status during playback.
- Hardware pointer before and after playback.
- ABOX trigger evidence.
- Source-versus-live comparison.
- Each route-script test.
- Every three-POW batch.
- Notes confirmation record.
- Boot sound readiness and logs.
- Reboot results.
- Post-boot audible confirmation.
- External route results and limitations.

Do not store unrelated Notes content.

Store only the active test title, its relevant note identifier, and the confirmation timestamp.

Create:

`docs/beta-finalization/live/PWNAGE-40000-REPORT.md`

Keep:

`docs/beta-finalization/live/PWNAGE-40000-TODO.md`

up to date.

---

# 21. FINAL REPORT

Report these sections:

## A. Actual root cause

Explain whether the missing `ABOX RDMA1_EN` setting was a direct cause on the live phone.

Explain any additional route, firmware, or startup readiness defects.

## B. Source/deployment mismatch

List the old repository behavior and the corrected persistent behavior.

## C. ABOX firmware

Explain whether Calliope reaches `MUB0` on every cold boot.

## D. Amplifier firmware

Report left and right CS35L41 DSP1 firmware readiness independently.

## E. PCM and PipeWire

Report actual PCM, 48 kHz rate, default sink and hardware-pointer behavior.

## F. Human confirmation

For every route:

- Exact output.
- Test-batch number.
- Three playback results.
- Notes observer method.
- Whether the fresh `works` title was detected.

## G. Startup behavior

Report whether the single startup POW is genuinely gated on audio readiness and whether the post-reboot audible test passed.

## H. Output support

List every physically tested output and all blocked routes.

## I. Remaining issues

Be honest about anything that remains unverified or requires kernel authorization.

## J. Evidence and rollback

Provide exact paths to reports, logs, modified files and rollback backups.

---

# FINAL NON-NEGOTIABLE INSTRUCTIONS

1. Do not start from scratch.
2. Preserve the most recent human-confirmed working audio path.
3. Do not deploy the stale route script over a better live configuration.
4. Resolve the `ABOX RDMA1_EN` contradiction.
5. Do not confuse Calliope core firmware with CS35L41 DSP1 protection firmware.
6. Require Calliope `MUB0` before considering the ABOX ready.
7. Use RDMA1 at 48 kHz and verify the actual runtime hardware parameters.
8. Verify the PipeWire default sink and handle failure correctly.
9. Use `pw-play` through the intended sink.
10. Play exactly THREE `nuxel-pow.mp3` invocations per manual confirmation batch.
11. Wait for the user's fresh `works` title in Notes.
12. Keep the same diagnostic session alive between batches.
13. Make the route and initialization persistent.
14. Reboot and verify audio after a fresh boot.
15. Do not make unauthorized kernel or firmware changes.
16. Never claim audible success based only on software logs.

**We already heard Nuxel make sound. Find the working route, fix the missing persistent pieces, and make the penguin POW automatically and reliably.**

# PWNAGE-40000 — FINISH THE AUDIO. 🐧🔊
