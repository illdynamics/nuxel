# FULL-PWNAGE-40000 — FINAL PHYSICAL SPEAKER OUTPUT REPAIR
## Samsung Galaxy S10+ / beyond2lte — Evidence-Driven Amplifier, Boost, Speaker and Persistent Driver Fix

**Required model:** `deepseek-v4-pro-thinking` (Pro Thinking / highest available reasoning effort)  
**Mission:** PWNAGE-40000  
**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820  
**OS:** Nuxel, Fedora-based ARM64  
**Access:** Existing Wi-Fi SSH  
**Last recorded target:** `root@192.168.178.167` (verify that it is still the handset)  
**SSH identity:** `~/.ssh/wicked_wqn_id_rsa` (verify it exists; never display/copy it)  
**Playback asset:** `./assets/nuxel-pow.mp3`  
**Target transducer:** Physical built-in loudspeaker, not receiver/earpiece.

---

# 0. EXECUTIVE MISSION AND STOP CONDITION

The digital audio path has been repaired to a substantial degree, but the actual built-in loudspeaker remains silent during the latest owner-supervised experiments.

The owner has explicitly authorized continued investigation and repair. The owner will provide the final acoustic proof through the Nuxel Notes Title field.

This is not a request to report that ALSA, PipeWire, DSP, DMA, DAPM or a player is ready. The goal is sound emitted by the phone's physical loudspeaker.

**Keep investigating and making evidence-led changes until either (A) the owner confirms sound with a fresh `yes`/`works`, or (B) a specific missing external dependency/physical defect is proven and accurately reported. Do not falsely declare completion.**

The owner’s latest test protocol supersedes the earlier three-play batch:

- One play of `nuxel-pow.mp3` per test iteration.
- Exactly 30 seconds for the owner to react after that playback.
- `yes` or `works` = positive acoustic confirmation.
- `no` = explicit negative result.
- Empty for the complete 30-second window = negative result, but only when Notes input preflight passed.
- No other sound during the response window.

## Required model lock

Use `deepseek-v4-pro-thinking` for repository analysis, kernel-driver investigation, implementation, debugging and verification. Do not silently switch to a smaller model. If unavailable, report that explicitly rather than silently substituting.

---

# 1. WHAT THE LATEST ZIP ACTUALLY SAYS

Read these files first:

1. `audio.md`
2. `docs/beta-finalization/live/PWNAGE-40000-AUDIO-ROOT-CAUSE.md`
3. `docs/beta-finalization/live/PWNAGE-40000-REPORT.md`
4. `docs/beta-finalization/live/evidence/pwnage-43000/05-speaker-path-audibility-experiments.md`
5. `docs/beta-finalization/live/evidence/pwnage-40000/SOURCE-RECONCILIATION.md`
6. `kernel/s10plus/patches/README.md`
7. The current route, bridge, diagnostic and Notes detector implementations.

There is no literal `out.md` file in the uploaded archive. The owner's affirmative decision to continue is recorded in the PWNAGE-43000 speaker-path experiment file. Treat that as the approved direction.

The latest experiment file is the authoritative current-state evidence. Older `audio.md` and prior report statements about Notes input being unavailable must not override the newer preflight and explicit owner `no` responses.

## 1.1 Verified baseline

The latest live evidence records:

| Layer | Verified observation |
|---|---|
| ABOX Calliope | `MUB0` |
| CS35L41 left DSP1 protection | `booted=Y running=Y` |
| CS35L41 right DSP1 protection | `booted=Y running=Y` |
| ABOX RDMA1 | `ABOX RDMA1_EN=1` |
| ABOX speaker routing | SPKAMP enabled; SPKAMP_A/B select RDMA1 |
| ABOX digital path | SPUS IN1/OUT1, SIFS1 and UAIF1 widgets active |
| Amplifiers | Enable on, mute unmuted |
| AMP PCM Gain | 12/12 in the experiment (`GAIN_CTRL=0x193`) |
| DSP1 protection | Firmware/preload reported ready |
| PipeWire | `alsa_output.hw_0_1`, S16LE, stereo, 48000 Hz |
| RDMA1 | Actual RUNNING state and advancing `hw_ptr` observed |
| Player | `pw-play` returned 0 |
| Owner result | Explicit `no` after the SPEAKER/volume/DSP experiments |

These confirm the digital signal and much of the amplifier state. They do not establish that the physical loudspeaker has emitted sound.

## 1.2 Negative experiments that must not be repeated blindly

The valid owner-supervised evidence records:

- E1: `ABOX Sound Type=1` (SPEAKER), sink volume 25% — no sound.
- E2: same SPEAKER mode, sink 55% — owner typed `no`.
- E3: PCM Source ASP → DSP, with DSP1 and PCM Source DAPM widgets ON and PWR_CTRL2 changed from `0x21` to `0x3721` — owner typed `no`.

The owner input preflight passed for these experiments, so the negative reports are meaningful.

The device was restored afterward to:

- ABOX Sound Type VOICE (0).
- Left/Right PCM Source ASP (0).
- PipeWire sink volume 0.25.
- Current persistent route applied and verified.

Start from the current live state, not an assumed state. Do not repeat the three identical experiments unless a new diagnostic result provides a reason to vary a different parameter or stage.

---

# 2. ROOT-CAUSE LEAD: FINAL CS35L41 OUTPUT / BOOST STAGE

## 2.1 Pinned kernel and missing sequence

The build wrapper pins the target kernel to:

- Repository: `https://github.com/Linux4/android_kernel_samsung_exynos9820`
- Commit: `f7194c1d15eded1c2a1a4dc63825b26103435cc0`
- Kernel: Samsung downstream Linux 4.14.253
- Defconfig: `exynos9820-beyond2lte_defconfig`

The checked source `sound/soc/codecs/cs35l41.c` has `cs35l41_main_amp_event()` handling POST_PMU by applying the pup patch, setting `PWR_CTRL1.GLOBAL_EN`, handling DSP PAUSE/RESUME, and calling `cirrus_pwr_start()`.

It does not include the later upstream external-boost `CSPL_MBOX_CMD_SPK_OUT_ENABLE` sequence.

The companion `drivers/mfd/cirrus-pwr.c` `cirrus_pwr_start()` is the Passport power/thermal monitor lifecycle: it marks the amplifier active and queues work that updates the power/thermal algorithm. It is not proof that the external speaker output has been enabled.

This is a strong conditional driver lead. It is not yet a proven fix.

## 2.2 External boost is a hardware-specific condition

The newer upstream CS35L41 speaker-output sequence is specifically for external-boost hardware. It handles tight power-up sequencing to avoid a pop/click, uses mailbox command `CSPL_MBOX_CMD_SPK_OUT_ENABLE` (value 7) where compatible firmware supports it, and has a legacy register sequence for older firmware.

Firmware v0.28.0 and older does not support the mailbox command; the actual `fw_id_version` must be checked. Do not infer compatibility from an ambiguous `fw_id` string.

The modern binding distinguishes internal boost, external boost and shared-boost variants. External boost uses specific GPIO1/boost configuration. Do not apply that sequence merely because the speaker is silent.

## 2.3 Existing captured DTB is a clue, not proof

The archive includes a historical DTB at:

`scripts/s10plus-debug-pack/captures/20261015T065746Z-boot-image-10304/boot-image/fdt-00-at-22056960.dtb`

It identifies two CS35L40-compatible nodes:

- I2C address `0x40`, `dsp-part-name=cs35l40-bot` (documented bottom/SPEAKER amplifier).
- I2C address `0x41`, `dsp-part-name=cs35l40-rcv` (documented receiver amplifier).
- Both report `cirrus,boost-peak-milliamp=0x1004` (4100 mA).

That historical DTB does not include `cirrus,boost-type`, `cirrus,gpio1-output-enable` or `cirrus,gpio1-src-select` on those nodes. It includes GPIO2 configuration.

It does not prove the currently booted DTB is identical, nor does it classify the live boost topology.

**Do not write or port an external-boost-specific output-enable sequence until the current hardware topology is positively identified.**

## 2.4 Specific investigation targets

- Live `/sys/firmware/devicetree/base` nodes and properties for both I2C amplifiers.
- Actual CS35L40-compatible driver match and variant.
- Actual OTP/boost-mode interpretation where the driver exposes it.
- Boost converter type and board power topology.
- GPIO1/GPIO2 routing and function.
- External boost rail and enable lines, if physically present.
- Regulator supply dependencies and voltage/current status.
- Both DSP firmware versions, especially `fw_id_version`.
- `PWR_CTRL1`, `PWR_CTRL2`, `BOOST` status and documented read-only registers.
- CSPL mailbox status and errors.
- Power monitor / output-power telemetry.
- `ABOX SOUNDBOOST_A`, `ABOX SOUNDBOOST_B`, `ABOX SOUNDBOOST_EN` semantics.
- Right AMP `SPK` DAPM path and its actual channel input.
- Speaker connector/transducer supply and amplifier output state.

Use read-only interfaces first. Never access a protected register by writing arbitrary values just to see what happens.

---

# 3. THE RIGHT AMP / PHYSICAL SPEAKER DISTINCTION

The codebase documents:

- `Right AMP SPK` maps to physical `SPEAKER`.
- `Left AMP SPK` maps to `RECEIVER`.
- The button manager therefore uses `Right AMP PCM Gain` as the external-speaker volume control; `Left AMP PCM Gain` does not drive the built-in SPEAKER endpoint.

Verify this live. Do not trust a stale comment if current routing differs.

During an active playback, record:

1. Right AMP DAPM path and physical output widget.
2. Left AMP receiver path separately.
3. Channel map and actual PCM samples.
4. Right AMP enable, mute, PCM Gain and Digital PCM Volume.
5. Right DSP1 state and firmware metadata.
6. Boost/output enable state.
7. Output-power telemetry.
8. Relevant regulator and GPIO state.

Receiver output is not speaker success. A widget named `SPEAKER` being ON is not proof of audible output.

---

# 4. USE THE NEW READ-ONLY SPEAKER DIAGNOSTIC FIRST

The patched source package adds:

`tools/s10plus/a33/nuxel-cs35l41-speaker-diag.sh`

It is deliberately read-only. It captures:

- System and audio service state.
- Live I2C amplifier devices.
- Live device-tree properties, including boost type and GPIO configuration.
- ALSA cards and PCM status/hardware parameters.
- PipeWire socket, sinks, default sink and volume.
- Targeted mixer readbacks, including SoundBoost and speaker-output power telemetry.
- DSP debugfs state and DAPM widgets where already exposed.
- Read-only regmap snapshots where debugfs is already mounted.
- Filtered kernel audio logs.
- Optional concurrent PCM watcher and periodic read-only amplifier output-power/SoundBoost telemetry during a test.

It does not play audio, write mixer controls, write sysfs, change GPIO, write regmap, restart services or mount debugfs.

On the phone, after deployment:

```bash
sudo /usr/local/sbin/nuxel-cs35l41-speaker-diag.sh \
  --out /root/pwnage-40000/speaker-final/baseline
```

For a one-play test, start the watcher first in a terminal/session that remains running:

```bash
sudo /usr/local/sbin/nuxel-cs35l41-speaker-diag.sh \
  --out /root/pwnage-40000/speaker-final/test-01 \
  --watch-seconds 4 --interval-ms 25
```

The watcher itself never starts playback. During that 4-second capture, separately initiate exactly one agreed POW using the verified PipeWire session environment. Inspect `60-playback-watch.jsonl`, `30-mixer-readbacks.txt`, `40-dsp-dapm-registers.txt`, and `50-kernel-audio-log.txt` together.

Run with sufficient permissions to read debugfs/regmap if already mounted. Do not mount debugfs solely for this mission unless explicitly justified; record unavailable telemetry honestly.

---

# 5. HUMAN CONFIRMATION: NOTES TITLE HANDSHAKE

## 5.1 Actual agreement

The owner will keep Notes open, the Title field focused, and the screen awake.

Per test:

1. Tell the owner the test number and the setting being tested.
2. Play `nuxel-pow.mp3` exactly once.
3. Wait a full 30 seconds.
4. Watch the active Notes Title field.
5. Classify the result:
   - fresh `yes` → PASS;
   - fresh `works` → PASS;
   - fresh `no` → FAIL;
   - empty for the full 30 seconds → FAIL if preflight passed;
   - other text → do not infer; ask/continue only after classifying safely.
6. Record the result and evidence before making the next change.

No other test tones, notification cues, volume feedback, startup cues or repeated POWs may play during that 30-second period.

## 5.2 Existing Notes detector

Use:

`tools/s10plus/a33/notes-works-detector.py`

The known deployed executable path in the archive is:

`/usr/local/bin/nuxel-notes-works-detector`

One previous log tried `/usr/libexec/nuxel/notes-works-detector.py`, which did not exist. Resolve this path discrepancy and use one correct, documented executable.

The current source detects the actual Notes Title field with AT-SPI, discovers the session AT-SPI bus before importing `gi`, uses the Notes store (`nuxel-notes`) for positive confirmation where available, and distinguishes:

- exit 0: fresh positive `yes`/`works`;
- exit 1: timeout;
- exit 2: Notes/AT-SPI/input channel unavailable;
- exit 3: fresh explicit `no`.

Run the detector with a **30-second timeout per test**. Use the current active note and baseline, not stale text in another note.

## 5.3 Preflight remains mandatory

The latest 05 experiment confirms the input-channel preflight succeeded in that session, and the owner typed `no`. Nevertheless, revalidate it at the start of the new session or after a reboot:

- Notes actually open.
- Active Title visible, focused and editable.
- Screen awake.
- Owner can physically type `ready` (or another preflight word).
- Live AT-SPI sees it.
- Notes app model reflects it.
- Autosave/storage is corroborated where available.
- Title reset to empty for first test baseline.

Do not type/inject the preflight value programmatically; the owner must do it.

If preflight fails, repair the input/observer mechanism first. A missing text response cannot prove silence while the confirmation channel is broken.

Do not read, export or log unrelated Notes content. Only capture the active Title and note ID needed for this test.

## 5.4 One continuous iteration session

Keep the SSH session, diagnostics, watcher and mission state alive between tests. Do not make the owner restart the whole agent after every negative result.

Use a monotonic clock for each 30-second response window. Do not start another test until the previous window is resolved and its result saved.

---

# 6. CURRENT BASELINE AND WHAT NOT TO REPEAT BLINDLY

The latest evidence restored and verified:

- Sound Type = VOICE (0).
- Left/Right PCM Source = ASP (0).
- PipeWire sink volume = 0.25.
- Route state = applied.

The following experiments produced no sound and should not be repeated unchanged:

- Sound Type SPEAKER (1) at 25% sink.
- Sound Type SPEAKER (1) at 55% sink.
- Sound Type SPEAKER (1) plus PCM Source DSP.

The experiment set included `pw-play` rc0 and active RDMA1/DAPM but no acoustic output.

Before testing any new setting, capture the actual live values. Do not assume the handset is still at the archived restored baseline.

Do not repeat gain 12 as though it were an acoustic confirmation. It is a measured/verified digital amplifier state only.

---

# 7. INVESTIGATE FINAL AMPLIFIER OUTPUT, BOOST AND POWER TELEMETRY

This is the core engineering task.

## 7.1 Interpret the driver correctly

In the pinned downstream driver's `cs35l41_main_amp_event()`:

- POST_PMU applies the pup patch.
- Sets PWR_CTRL1.GLOBAL_EN.
- Handles DSP pause/resume.
- Calls `cirrus_pwr_start()`.

`cirrus_pwr_start()` is not speaker-output enable. It marks the amp active and triggers Passport thermal/power-monitor work.

The newer upstream external-boost speaker output sequence is separate. If topology is external boost, assess whether this missing sequence leaves the amplifier's final output stage disabled despite the digital path running.

## 7.2 Verify boost type on the actual live handset

Do not use the historical DTB as conclusive current hardware evidence.

Capture the current live device tree and inspect each amplifier node.

Use the diagnostic script to capture:

- compatible;
- reg/address;
- boost type;
- boost peak current;
- boost inductor/capacitance properties if present;
- GPIO1 output-enable and source-select;
- GPIO2 configuration;
- status and supplies.

Also inspect the exact pinned kernel driver's probe path and OTP decoding, if any. Determine which source is authoritative for the board's boost topology.

If topology cannot be determined with confidence, do not apply a topology-specific register/mailbox sequence. Escalate the missing evidence rather than guessing.

## 7.3 External-boost conditional path

Only when the live board is positively identified as external boost:

- Compare the pinned 4.14.253 driver with the relevant upstream CS35L41 external-boost change.
- Port the entire correct sequence, not a partial register write.
- Check the exact DSP firmware `fw_id_version`.
- Use `CSPL_MBOX_CMD_SPK_OUT_ENABLE` only for firmware that supports it.
- Honor the documented old-firmware fallback (v0.28.0 and older do not support the new mailbox command).
- Implement the complete safe power-up sequence, protected register/test-key requirements, state polling, error handling, and power-down counterpart.
- Apply to the correct amplifier(s) only.
- Preserve CS35L41 DSP1 protection and thermal policy.
- Handle DAPM event ordering, suspend/resume and failure rollback.
- Add driver tests or testable helpers where the old kernel allows.
- Validate patch applies to the exact pinned source commit.

Never execute the external-boost sequence from userspace through sysfs/register writes.

Never disable protection firmware or thermal management.

## 7.4 Internal/shared boost path

If the live topology is internal or shared boost, do not apply the external-boost command blindly.

Inspect the topology-specific enable sequence in the exact downstream driver and matching upstream/vendor implementation. Determine whether the final power stage is expected to be enabled by another boost, GPIO, regulator, ABOX SoundBoost, amp DAPM, or board-specific sequence.

The goal is to identify the actual missing stage, not to enable every potential control.

## 7.5 Output-power telemetry

During one real playback, observe:

- `Left DSP1 Protection cd PL_SPK_OUTPUT_POWER`.
- `Right DSP1 Protection cd L_SPK_OUTPUT_POWER`.
- Exposed `/sys/class/cirrus` or platform power-left/right telemetry.
- ABOX SoundBoost controls and state.
- Any documented output-current or voltage telemetry.

Idle zero values are not evidence of failure. Compare before/during/after active playback and understand scaling/update timing.

If both digital DSP paths run but amplifier output-power telemetry remains zero, use that result to distinguish DSP input from final output enable/power-stage failure.

If telemetry rises while no sound is heard, investigate the speaker transducer, wiring, connector, output mute, and physical endpoint (with owner-safe inspection only). Do not infer a broken speaker before validating the power stage.

## 7.6 ABOX SoundBoost controls

The old snapshot recorded:

- `ABOX SOUNDBOOST_A=0` (None)
- `ABOX SOUNDBOOST_B=0` (None)
- `ABOX SOUNDBOOST_EN=0` (Off)

These are clues, not instructions to turn them on.

Find their exact driver/control semantics, enum values, DAPM relationship and intended S10+ topology. Check whether they are required for this route and how the vendor initializes them.

Only test them after mapping semantics. Change one controlled variable at a time, record prior values, read back, and restore on failure.

---

# 8. AUDIO SIGNAL, CHANNEL MAP AND PHYSICAL OUTPUT

The source MP3 is 44.1 kHz stereo, approximately 0.366 seconds. PipeWire is expected to resample to the 48 kHz RDMA1 hardware path.

Verify:

- Source checksum before and after deployment.
- Decoder output is nonzero and contains meaningful audio samples.
- Player is using `pw-play`.
- Player gain is explicitly 1.0 unless evidence supports otherwise.
- PipeWire stream connects to `alsa_output.hw_0_1`.
- Actual channel map is correct.
- Right-channel samples are not silent.
- Right AMP receives active samples.
- The physical SPEAKER path is the right channel/output, as documented.
- The receiver path is not being mistaken for loudspeaker output.

Use silent signal analysis where possible; do not play diagnostic sine waves during the owner's confirmation window.

Do not synthesize a different test sound in place of `nuxel-pow.mp3`. The agreed acoustic proof must use the owner's asset.

---

# 9. VOLUME AND MUTE POLICY

The known-good baseline uses AMP PCM Gain 12/12, but the right channel is the relevant external SPEAKER path. The current evidence shows `GAIN_CTRL=0x193`, `DIG_VOL_CTRL=0x8000`, mute unmuted.

Preserve this baseline unless output-path telemetry identifies a reason to change it.

Do not increase analog amplifier gain arbitrarily. Do not disable DSP protection, thermal protections, or hardware limiter.

Check:

- Nuxel sound-mode policy;
- `/var/lib/nuxel/audio/sound-mode`;
- PipeWire sink mute and volume;
- `pw-play` software volume;
- amplifier mute and gain;
- codec/ABOX digital attenuation;
- any duplicated attenuation stage.

The static PipeWire sink opens `hw:0,1` directly and bypasses the ALSA `softvol` default chain. The actual PipeWire sink volume is therefore a separate control and must be read live.

If a software-volume change is justified, change only the intended PipeWire sink level, in measured steps and with a conservative ceiling. Log the real sink percentage and player volume separately. Do not combine sink attenuation with an additional player gain that makes the effective output unexpectedly tiny.

The prior experiment at 55% did not produce sound, so do not simply keep raising volume as the main strategy. Focus on the final output stage.

For manual test use the single verified playback path:

```bash
pw-play --volume 1.0 /usr/share/nuxel/assets/nuxel-pow.mp3
```

Run it in the same PipeWire runtime/session used by the Nuxel UI. Verify the current `XDG_RUNTIME_DIR`, `PIPEWIRE_RUNTIME_DIR`, pulse socket and target user before invoking it. Do not guess the session environment.

---

# 10. REAL-TIME OBSERVATION OF THE 366 MS PLAYBACK

The latest experiments sometimes collected PCM state only after the short MP3 had completed. That can miss RUNNING state and output telemetry.

The new read-only diagnostic watcher was added specifically to improve this.

For each test:

1. Start a 4-second diagnostic capture with `--watch-seconds 4 --interval-ms 25`.
2. Ensure its watcher is live before playback.
3. Start exactly one `pw-play` of the deployed asset.
4. Record process start and exit status.
5. Capture the concurrent JSONL samples.
6. Verify PCM `RUNNING`, 48 kHz, pointer advance and stream route.
7. Examine sampled amplifier output-power/SoundBoost telemetry.
8. Examine DAPM and kernel logs.
9. Let the owner have the full 30 seconds after the playback.

Do not assume a player process with exit code zero sent sound to the right output.

Do not claim that DMA movement proves the transducer is powered.

Keep the diagnostic read-only. It must never alter controls or service state.

---

# 11. NOTES HANDSHAKE AND ITERATION LOOP

## 11.1 Detector source and deployed path

Source:

`tools/s10plus/a33/notes-works-detector.py`

Known deployed path:

`/usr/local/bin/nuxel-notes-works-detector`

One older attempt incorrectly used `/usr/libexec/nuxel/notes-works-detector.py`, which did not exist. Do not repeat that path error.

Check source/deployed hash parity and repair deployment if needed.

The detector currently:

- Discovers the session AT-SPI bus before importing `gi`.
- Identifies the live Notes Title entry.
- Requires field focused/showing/editable.
- Captures a fresh baseline.
- Accepts `yes` and `works` as positive responses.
- Accepts `no` as a negative response.
- Corroborates positive input against the `nuxel-notes` store where that RPC is available.

Exit conventions:

- `0`: PASS — fresh `yes`/`works`.
- `1`: TIMEOUT — no response within the requested deadline.
- `2`: Notes/AT-SPI unavailable or invalid confirmation channel.
- `3`: NEGATIVE — fresh `no`.

Use `--timeout 30` for every playback test.

## 11.2 Preflight

At the start of a new live session and after every reboot:

- Unlock phone.
- Open Notes.
- Focus Title field.
- Ensure it is visible and editable.
- Ensure screen stays awake during test.
- Have owner type `ready` (or a distinct preflight value).
- Verify fresh text through AT-SPI and Notes app model/store where available.
- Clear Title to an empty baseline.

The latest 05 experiment says preflight passed and owner typed `no`, but revalidate after deployment/session restart.

If input preflight fails, fix it before audio tests. Empty field while the input channel is broken is not a valid negative acoustic result.

## 11.3 Per-test procedure

For each iteration:

1. Announce test number, the single setting/change and current output level.
2. Record live baseline values.
3. Capture 4-second live diagnostic watcher.
4. Start Notes detector with a 30-second monotonic timeout and fresh baseline.
5. Trigger one playback of `nuxel-pow.mp3` exactly once.
6. No additional sounds for 30 seconds.
7. Collect detector outcome.
8. Record explicit `yes`, `works`, `no`, timeout, or input-channel error.
9. Preserve logs and exact settings.
10. If negative, inspect evidence and determine the next single logical experiment.
11. Reset the Notes Title to empty and verify the next baseline.
12. Repeat without restarting the whole mission/SSH session.

Do not start a second playback until the 30-second response window is closed.

Do not automatically repeat sound.

Do not assume blank means no sound if Notes preflight failed.

When positive `yes`/`works` occurs, immediately preserve the settings and stop experimenting with that working route.

---

# 12. DRIVER FIX DECISION TREE

## Case A — Live topology is external boost

If current live DT/OTP/board evidence positively identifies external boost and the pinned 4.14 driver lacks its required speaker-output enable sequence:

1. Obtain the exact upstream implementation/reference diff and associated compatibility corrections.
2. Read the entire affected driver path, not just the new mailbox constant.
3. Compare against the pinned 4.14.253 `cs35l41.c`, CSPL mailbox implementation, regmap/test-key APIs and DSP metadata structures.
4. Port the complete sequence to the old APIs.
5. Use `fw_id_version` with the correct version boundary. The documented mailbox command is unsupported by firmware v0.28.0 and older; use the compatible legacy sequence for those versions only if the upstream/vendor code confirms it.
6. Preserve the correct DAPM event order.
7. Make the sequence per-amplifier and topology-aware.
8. Handle mailbox failure, timeout, device suspend, shutdown and power-down.
9. Lock test keys on every success/failure path.
10. Preserve DSP1 protection and thermal policy.
11. Add diagnostic log lines showing which sequence was selected and why, without sensitive data.
12. Build against the exact pinned tree and validate no unrelated files changed.
13. Test driver behavior first with the safest available hardware evidence; then owner one-play confirmation.

Do not issue userspace writes to CS35L41 protected registers as a replacement for this driver logic.

## Case B — Live topology is internal/shared boost

Do not use the external-specific SPK_OUT_ENABLE sequence.

Investigate the actual expected internal/shared boost path, including supply/regulator, GPIO and DAPM sequencing, boost converter readiness, output power, SoundBoost, amplifier output enable, and board-specific driver data.

Port only a sequence proven to match the live topology and correct silicon/firmware revision.

## Case C — Telemetry indicates DSP receives no useful signal

Investigate ABOX PCM channel map, RDMA samples, DSP input path and source routing. Do not change the output-boost stage until input evidence indicates signal reaches DSP.

## Case D — DSP output power is active but no speaker sound

Investigate output enable, boost, speaker supply, routing, physical connector/transducer and the board's analog stage. Do not keep changing PipeWire when the signal is already reaching the final amplifier stage.

## Case E — Power telemetry remains unavailable

If the driver/firmware does not expose reliable output-power telemetry, do not interpret missing telemetry as zero. Find another supported read-only measurement or state that the exact point remains unknown.

---

# 13. KERNEL PATCH BUILD PIPELINE — A RECENTLY FIXED REPOSITORY DEFECT

The updated repository now includes an idempotent patch-application phase in:

`kernel/s10plus/build-kernel.sh`

The previous wrapper claimed to apply `kernel/s10plus/patches/*.patch` but had no `git apply` step. The replacement wrapper now:

- Applies patches in lexical order.
- Skips the explicit `# STUB` documentation patch.
- Detects already-applied patches.
- Runs forward `git apply --check`.
- Applies the patch.
- Performs a reverse check.
- Writes a log to `.build/out/patch-application.log`.
- Warns on optional patch conflict.
- Supports a `<patch>.required` marker for a mandatory patch.

Before relying on this feature:

- Inspect the implementation in the supplied tree.
- Run shell syntax checks.
- Test patch apply/reverse behavior in a disposable copy of the exact pinned source when network/source availability permits.
- Ensure a required patch failure stops before compilation.
- Never let an optional patch failure be mistaken for an applied fix.

Any new mandatory CS35L41 driver fix must add the `.required` sidecar only after validated applicability against the pinned commit.

**The kernel build script being able to apply patches does not authorize a kernel flash.**

---

# 14. PERSISTENCE AND BOOT INTEGRATION

Only after the owner confirms audible speaker output:

1. Identify the exact settings/driver sequence that produced the sound.
2. Add it to the correct persistent source, not only a live terminal command.
3. Ensure the route applies only to the correct S10+ amp/topology.
4. Add readback checks to `nuxel-audio-route.sh` or the driver readiness logic as appropriate.
5. Preserve ABOX `MUB0` and both DSP1 readiness requirements.
6. Preserve RDMA1 48 kHz static PipeWire sink.
7. Ensure retry units do not repeatedly reset amplifier state or gain.
8. Ensure boot sound occurs only once after complete speaker readiness.
9. Ensure speaker readiness is reported separately from physical audibility.
10. Add tests that fail if the known speaker-enable sequence is removed or skipped.
11. Reboot only after backups and rollback are prepared.
12. Verify route after cold boot.
13. Perform a fresh one-play / 30-second owner confirmation.

Do not make the first startup cue or the diagnostic process a prerequisite for audio operation.

---

# 15. DEPLOYMENT AND AUTHORIZATION BOUNDARIES

The owner authorizes normal software/kernel-source changes needed to fix the audio path, but the current task must preserve the physical phone and its recovery options.

Allowed during this mission:

- Read-only diagnostics.
- Correct ALSA controls with known semantics and bounded rollback.
- PipeWire routing/configuration fixes.
- Bridge and Nuxel audio source fixes.
- Build a local kernel image if the external/internal boost diagnosis proves a driver change necessary.
- Add and validate a kernel patch against the pinned source.
- Stage the resulting artifact and provide a separate explicit deployment decision.

Not authorized by this task:

- TWRP reflash.
- Boot image or kernel flashing.
- Bootloader modification.
- Modem/EFS/firmware partition writes.
- Repartition or format.
- Disabling amplifier thermal/protection firmware.
- Arbitrary protected-register writes from userspace.

Do not flash the newly built kernel automatically. If the required fix is kernel-level, build and validate it locally, report the exact changes/artifact and request separate explicit authorization before flashing.

Preserve Wi-Fi SSH. Do not power-cycle or intentionally disconnect WLAN as part of speaker tests.

---

# 16. REQUIRED AUTOMATED TESTS

Add/update tests for:

- Diagnostic CLI help and read-only guarantee.
- No ALSA cset, sysfs write, GPIO write, regmap write, service restart or playback from the diagnostic script.
- PCM watcher captures status/hw_params concurrently.
- Output-power and SoundBoost telemetry sampling is read-only.
- Notes detector supports `yes`, `works`, and `no` with the documented exit codes.
- Notes preflight failure is not classified as silence.
- Route readiness does not claim speaker output just from DMA/DAPM.
- The driver fix is conditional on positively identified boost topology.
- External-boost firmware compatibility check uses `fw_id_version` and the correct threshold.
- Full external boost-up/down error paths preserve protection and test-key locks.
- Patch wrapper idempotence, conflict handling and required-patch failure.
- No regression to existing audio boot readiness and RDMA1 48 kHz behavior.

Do not add fake physical-audio tests. Hardware acceptance requires the owner confirmation.

---

# 17. PHYSICAL TEST PROCEDURE

After every controlled change:

- The phone remains unlocked with Notes open.
- Title field is focused, visible and editable.
- The screen remains awake using a supported inhibitor/timeout setting. Do not write directly to panel backlight sysfs.
- The test watcher is started before playback.
- The Notes detector captures a fresh baseline.
- The owner is told exactly when to listen.
- One POW is played once.
- The owner receives a full 30 seconds to react.
- `yes`/`works` is positive; `no`/empty is negative.
- No more sound is played during that response window.

If the screen sleeps or the Notes app loses focus, pause the test loop and restore the input confirmation channel without changing the audio controls.

Once audible output is confirmed, do not continue random experimentation. Preserve the exact successful settings immediately.

---

# 18. ACCEPTANCE MATRIX

Mark each PASS / FAIL / BLOCKED / NOT TESTED. Evidence is mandatory.

| ID | Requirement | Evidence |
|---|---|---|
| DOC-01 | User's affirmative direction found | Latest 05 experiment read |
| BASE-01 | Current live baseline captured | Diagnostic snapshot |
| BASE-02 | Latest verified ABOX/DSP path preserved | Readbacks |
| OUT-01 | Live boost topology identified | DT/OTP/driver evidence for both amps |
| OUT-02 | Correct final output-enable path understood | Exact source/driver sequence |
| OUT-03 | SoundBoost semantics understood | Driver/control mapping |
| OUT-04 | Output-power telemetry interpreted | Before/during/after capture |
| MAP-01 | Right AMP physical SPEAKER verified | Current DAPM/channel map |
| PCM-01 | RDMA1 48 kHz retained | Runtime hw_params/status |
| PCM-02 | PCM/hw_ptr during play | Concurrent watch JSONL |
| PW-01 | Correct default PipeWire sink | Live readback |
| PW-02 | Actual stream linked to intended sink | PipeWire link evidence |
| DSP-01 | Both CS35L41 DSP1 remain protected/running | Live debugfs/logs |
| NOTE-01 | Notes preflight | Real owner-entered ready |
| NOTE-02 | 30-second loop works | Fresh detector results |
| TEST-01 | First positive acoustic test | Fresh `yes`/`works` |
| PERSIST-01 | Fix committed to persistent route/driver | Source diff and deploy hash |
| BOOT-01 | Post-boot hardware state | New boot evidence |
| BOOT-02 | Fresh post-boot acoustic test | Fresh `yes`/`works` |
| SAFE-01 | DSP/thermal protection preserved | Driver/config review |
| SAFE-02 | Recovery and Wi-Fi SSH preserved | Reconnect evidence |
| SAFE-03 | No TWRP/kernel flash without authorization | Deployment record |

---

# 19. EVIDENCE AND DELIVERABLES

Create/update:

- `docs/beta-finalization/live/PWNAGE-40000-TODO.md`
- `docs/beta-finalization/live/PWNAGE-40000-REPORT.md`
- `docs/beta-finalization/live/PWNAGE-40000-AUDIO-ROOT-CAUSE.md`

Create a new evidence run directory:

`docs/beta-finalization/live/evidence/pwnage-40000/final-speaker-<UTC timestamp>/`

Include:

- Initial live device state.
- Actual live DT/boost topology for both amplifiers.
- Driver source/commit and relevant diff.
- DSP firmware version metadata.
- Output-power telemetry before/during/after each relevant test.
- ABOX SoundBoost state and semantics.
- Right AMP/SPK path evidence.
- Current ALSA and PipeWire state.
- Every one-play experiment and setting.
- Notes preflight and response result.
- First positive acoustic confirmation.
- Persistent route/driver patch.
- Build and patch-application logs if applicable.
- Post-reboot readbacks and acoustic confirmation.
- Rollback steps.

Do not dump unrelated notes or user documents. Do not log exact private locations or credentials.

---

# 20. FINAL REPORT

Report:

1. **Actual final-stage root cause:** exact missing enable, power, route or hardware dependency. If not proven, state what remains unknown.
2. **Boost topology:** internal/external/shared, with evidence for each amplifier.
3. **Driver fix:** precise source change and why it matches the confirmed topology/firmware.
4. **Speaker route:** Right AMP → physical speaker, output enable, gain, mute and DAPM state.
5. **Runtime signal:** RDMA1, PipeWire sink, links, hardware pointer and output telemetry.
6. **Owner confirmation:** first fresh `yes` or `works`, test ID and exact settings.
7. **Persistence:** source/stage/deployed hashes and boot service state.
8. **Post-boot confirmation:** a fresh owner audible confirmation after a reboot.
9. **Remaining limitations:** exact blocked dependencies.
10. **Safety:** protection, thermal control, Wi-Fi SSH and recovery retained.
11. **Rollback:** exact backup/artifact and steps.

---

# FINAL NON-NEGOTIABLE RULES

1. Do not restart audio from scratch.
2. Preserve the currently verified Calliope/DSP1/RDMA1/PipeWire path.
3. Read the latest PWNAGE-43000 experiment; honor its valid negative results.
4. Focus on the final amplifier power/boost/output stage.
5. Verify live boost topology before any external-boost-specific patch.
6. Understand ABOX SoundBoost controls before changing them.
7. Sample output-power telemetry during playback, not just idle.
8. Keep the Right AMP physical SPEAKER path distinct from the receiver.
9. One POW per test, then a complete 30-second human response window.
10. Do not play other audio during that window.
11. A broken Notes input channel is not an audio failure.
12. Do not accept player exit code, DMA movement or DAPM state as audibility.
13. Keep iterating after every valid negative response.
14. Persist the first configuration that the owner actually confirms.
15. Reboot only after a confirmed fix is persistent and recoverable.
16. Require a fresh post-boot `yes`/`works`.
17. Never disable CS35L41 protection or thermal management.
18. Never perform arbitrary register writes from userspace.
19. No TWRP reflash or kernel/boot flashing without separate explicit authorization.
20. Preserve Wi-Fi SSH and the existing recovery path.

**This is the final physical speaker repair. A green software status is not the finish line. The finish line is the actual Nuxel POW from the S10+ loudspeaker, confirmed by the owner.**

# PWNAGE-40000 — FINISH THE SPEAKER. 🐧🔊
