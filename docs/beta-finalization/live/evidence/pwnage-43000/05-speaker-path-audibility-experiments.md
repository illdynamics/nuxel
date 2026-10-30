# PWNAGE-43000 — Physical speaker-path audibility experiments

**Date:** 2026-10-30
**Target:** root@192.168.178.167 (S10+ beyond2lte) over Wi-Fi SSH
**Key:** ~/.ssh/wicked_wqn_id_rsa

## Owner decision
out.md question answered: **yes, continue with the physical-audibility /
speaker-path issue**. The pre-wayland ABOX reload fix itself remains
non-shippable until the CS35L41 protection-DSP load path is fixed
independently.

## Baseline (known-good, verified before experiments)
- Calliope `MUB0`; both CS35L41 DSP1 `booted=Y running=Y` with
  `cs35l40-bot/rcv-dsp1-spk-prot.{wmfw,bin}`.
- Route `state=applied`: RDMA1_EN=1, SPKAMP_EN=1, SPKAMP_A/B=RDMA1,
  SPUS IN1=RDMA, SPUS OUT1=SIFS1, SIFS1=SPUS OUT1, UAIF1 SPK=SIFS1,
  UAIF1/SIFS1 OUT switches on.
- Amps: enable on, mute=Unmuted, PCM Gain=12/12, DSP1 Protection preload on,
  PCM Source=ASP/ASP.
- PipeWire default sink `alsa_output.hw_0_1`, s16le 2ch 48000 Hz, volume 0.25.
- Notes Title live, focused, showing, editable, empty (input channel preflight
  passed this session; owner successfully typed `no` during tests).

## Controlled experiments (one variable at a time)

### E1: ABOX Sound Type VOICE -> SPEAKER (1), sink 25%
- Readback `1`; `pw-play` rc=0.
- Owner Notes Title: empty for 30 s => no audible sound.

### E2: ABOX Sound Type=SPEAKER, sink 55%
- `pw-play` rc=0.
- Owner Notes Title: `no` => **no audible sound** (confirmed negative).

### E3: PCM Source ASP -> DSP (CS35L41 DSP1 in audio path), Sound Type=SPEAKER
- DAPM change observed during playback: `Left/Right DSP1` and `PCM Source`
  widgets go from Off to **On** (previously DSP1 bypassed by ASP).
- `PWR_CTRL2` changes 0x21 (ASP) -> 0x3721 (DSP) in driver log; `pw-play` rc=0.
- Owner Notes Title: `no` => **no audible sound** (confirmed negative).
- (One contaminated baseline run was discarded and rerun clean.)

## What the live path shows during playback (both ASP and DSP modes)
- CS35L41: Main AMP On, AMP SPK On, CLASS H On, AMP Playback On, PCM Source On;
  DSP1 On only in DSP mode.
- ABox: SPUS IN1/OUT1, SIFS1, SIFS1 OUT, UAIF1 SPK, UAIF1 PLA all On.
- Driver logs at each play: `cs35l41_pcm_mute: Unmuted`, `GAIN_CTRL=0x193`,
  `DIG_VOL_CTRL=0x8000` (unity/0 dB), `PWR_CTRL1=0x1`,
  `PWR_CTRL2=0x21` (ASP) or `0x3721` (DSP).
- `pw-play` rc=0 every time; no CS35L41 mailbox/CSPL error in dmesg.

## Conclusion
The entire software/ALSA/DAPM/ABox/CS35L41-DSP path is measurably active and
unmuted up to the amplifier, yet the owner reports no audible sound for both
PCM Source modes, both ABOX Sound Type modes, and sink volumes 25%/55%.

This points at the final analogue/output stage or a vendor-driver-specific
speaker-output enable step (for example the upstream CS35L41 DSP path sends a
`CSPL_MBOX_CMD_SPK_OUT_ENABLE` mailbox command on the running DSP), not at the
already-fixed digital route. Physical speaker/hardware output has **not** been
claimed working.

## Restored state
Known-good configuration restored and re-verified:
- ABOX Sound Type=VOICE(0); Left/Right PCM Source=ASP(0); sink volume 0.25.
- `nuxel-audio-route.sh` rerun -> `route applied and verified`.
- Calliope MUB0; both CS35L41 DSP1 `booted=Y running=Y`; route `state=applied`.

Evidence directories on device: /root/pwnage-40000/speaker-soundtype-test,
/root/pwnage-40000/volume-55-test, /root/pwnage-40000/test-pcmsource-dsp*,
/root/pwnage-40000/speaker-test-4-45s.
