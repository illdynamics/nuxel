# PWNAGE-40000 — FINAL S10+ SPEAKER OUTPUT FIX

**Required model:** `deepseek-v4-pro-thinking`  
**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820  
**Access:** Existing Wi-Fi SSH  
**Last recorded host:** `root@192.168.178.167`  
**SSH identity:** `~/.ssh/wicked_wqn_id_rsa`  
**Source sound:** `./assets/nuxel-pow.mp3`  
**Goal:** Make the physical built-in loudspeaker audible, confirm it with the owner, and make the proven fix persistent.

## Important: the latest investigation has already narrowed the fault

The latest evidence in `docs/beta-finalization/live/evidence/pwnage-43000/05-speaker-path-audibility-experiments.md` records valid owner-supervised negative tests. The Notes input preflight passed; the owner typed `no` after the tests.

The following digital-path components are already verified and must not be rebuilt blindly:

- ABOX Calliope reports `MUB0`.
- Both CS35L41 DSP1 protection processors report booted/running.
- `ABOX RDMA1_EN=1`; RDMA1 → SPUS → SIFS1 → UAIF1 is applied.
- Both amplifier enable/mute controls read enabled/unmuted.
- Tested AMP PCM Gain was 12/12 (`GAIN_CTRL=0x193`).
- PipeWire default sink is `alsa_output.hw_0_1`, stereo 48 kHz.
- RDMA1 reaches RUNNING and the hardware pointer advances during playback.
- `pw-play` exits successfully.

These facts prove a substantial digital path, **not audible physical output**.

## Main remaining lead

The pinned downstream 4.14.253 CS35L41 driver runs `cs35l41_main_amp_event()` through global power enable, DSP pause/resume and `cirrus_pwr_start()`. That power helper is the Passport/thermal power-monitor lifecycle; it is not the later speaker-output enable command.

Newer upstream CS35L41 code has an explicit `CSPL_MBOX_CMD_SPK_OUT_ENABLE` sequence for **external-boost hardware**. The exact S10+ boost topology is not yet proven. A historical DTB contains CS35L40-compatible amp nodes but no `cirrus,boost-type` or GPIO1 external-boost configuration. Do not blindly apply an external-boost sequence. First inspect the live DT, OTP/driver interpretation, per-amp boost configuration and physical power topology.

The archived mixer inventory also showed `ABOX SOUNDBOOST_A/B/EN` as None/None/Off, while dynamic `PL_SPK_OUTPUT_POWER` / `L_SPK_OUTPUT_POWER` telemetry was zero in an **idle** snapshot. Their semantics and values during playback are not yet known.

## Required order

1. Read `docs/beta-finalization/live/PWNAGE-40000-AUDIO-ROOT-CAUSE.md` and the latest PWNAGE-43000 speaker experiment.
2. Connect over the existing Wi-Fi SSH session; preserve it.
3. Run the new read-only `tools/s10plus/a33/nuxel-cs35l41-speaker-diag.sh` and capture live DT/OTP/boost topology, mixer state, DAPM, PCM, PipeWire, DSP state and output-power telemetry.
4. Confirm the Notes detector is healthy before audio tests. The current detector is `tools/s10plus/a33/notes-works-detector.py`; the known deployed path is `/usr/local/bin/nuxel-notes-works-detector`. It accepts fresh `yes`, `works`, and `no` responses. The old `/usr/libexec/nuxel/notes-works-detector.py` path was absent in one previous run.
5. Identify the exact final-stage failure from evidence. Do not repeat already-failed Sound Type SPEAKER, 55% sink, or PCM Source DSP tests unless new evidence specifically justifies a different, controlled variant.
6. If and only if external boost is positively identified, port the complete compatible upstream speaker-output enable/disable sequence into the pinned 4.14.253 driver. Include mailbox firmware-version compatibility, safe legacy sequence when required, test-key locking, sequencing, error handling and matching power-down behavior. Do not use userspace raw register writes.
7. If the board is internal/shared boost, identify the correct topology-specific setup instead. Investigate ABOX SoundBoost, CS35L41 boost controls, amplifier output-power telemetry, right-channel speaker mapping, supply/boost rails and missing codec/amp sequencing.
8. For each controlled change, play `nuxel-pow.mp3` exactly ONCE, then give the owner a full 30 seconds. `yes` or `works` means audible PASS; `no` or a full empty window means FAIL only if the Notes preflight passed. Do not play anything else during the response window.
9. Keep the same diagnostic session alive between tests. Record every change and result. Continue until the owner confirms audible output or a genuine external dependency is proven and documented.
10. Persist only the configuration/driver fix that produced owner-confirmed sound. Reboot only after the working fix is built, staged and backed up; then repeat the one-play/30-second owner confirmation after boot.

## Critical requirements

- Focus on the built-in SPEAKER, not receiver/earpiece, Bluetooth or headphones.
- `Right AMP SPK` is the documented physical SPEAKER path; `Left AMP SPK` maps to RECEIVER. Verify live.
- Preserve the known-good RDMA1 48 kHz PipeWire path and verified DSP protection firmware.
- Preserve AMP PCM Gain 12 as the measured baseline; do not raise amplifier analog gain or disable thermal/DSP protection blindly.
- Inspect output-power telemetry while playback is active; idle zero values are not diagnostic.
- Read and explain ABOX `SOUNDBOOST_A/B/EN` semantics before changing them.
- Use `pw-play` through the verified PipeWire sink; do not open an ALSA PCM directly while PipeWire owns it.
- Preserve the effective-volume policy and avoid double attenuation. Log actual sink/player gain separately.
- No TWRP reflash, kernel/boot image flashing, bootloader change, repartition or firmware-partition write. Build a kernel locally only if the conditional driver diagnosis proves it necessary; do not flash without separate explicit authorization.
- Preserve Wi-Fi SSH, user data, boot recovery and the present working configuration.

## Definition of done

The owner hears the built-in speaker and enters a fresh `yes` or `works` in the focused Notes Title field. The exact successful configuration is committed to the persistent route/driver path, then survives a normal reboot and another fresh owner-confirmed playback. A player exit code, DMA activity, DAPM state or DSP-ready flag is never a substitute for that confirmation.

**Do not stop at “audio ready”. Finish the physical speaker path.** 🐧🔊
