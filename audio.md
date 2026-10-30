# Nuxel S10+ audio — current status (2026-10-30, after speaker-path experiments)

Device: Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820
Userspace: Fedora 43 aarch64, PipeWire + WirePlumber

## Verdict

**Digital playback path verified; physical built-in speaker still silent in
owner-supervised tests and not fixed.** This is now a confirmed negative
result, not merely a missing confirmation: the PWNAGE-43000 speaker-path test
passed the Notes input preflight and the owner typed `no` during tests.

The complete digital path is substantially verified:

- ABOX Calliope reaches `MUB0`.
- Both CS35L41 DSP1 protection images report `booted=Y running=Y`.
- `ABOX RDMA1_EN=1` and the RDMA1 -> SPUS -> SIFS1 -> UAIF1 route is applied.
- Both amplifier enable/mute controls read back active/unmuted.
- The tested amplifier PCM gain was 12/12 (`GAIN_CTRL=0x193`).
- PipeWire selects `alsa_output.hw_0_1` at 48 kHz.
- RDMA1 becomes RUNNING and its hardware pointer advances during playback.
- `pw-play` exits successfully.

These do not prove physical sound. The speaker-path owner tests at the
following settings were negative:

- ABOX Sound Type SPEAKER (1), sink volume 25%: no audible output.
- ABOX Sound Type SPEAKER (1), sink volume 55%: owner typed `no`.
- CS35L41 PCM Source ASP -> DSP while SPEAKER mode was selected: owner typed
  `no`.

The configuration was restored to Sound Type VOICE (0), PCM Source ASP (0),
and sink volume 0.25. Do not repeat those same settings as the first
experiment without new evidence.

## Most important remaining investigation

Inspect the final CS35L40-compatible amplifier power/boost/output stage.

The pinned 4.14.253 kernel's `cs35l41_main_amp_event()` sets PWR_CTRL1
GLOBAL_EN and calls `cirrus_pwr_start()`, but does not include the later
upstream external-boost SPK_OUT_ENABLE sequence. `cirrus_pwr_start()` is the
Passport thermal/power-monitor lifecycle, not speaker-output enable.

However, the upstream SPK_OUT_ENABLE sequence is specifically for external
boost. A historical captured S10+ DTB shows CS35L40-compatible devices at I2C
0x40 (bottom/SPEAKER) and 0x41 (receiver), each with boost peak current 4100 mA,
but does not establish external boost or configure GPIO1 as an external boost
enable. Do not port or execute the external-only sequence until the live board
boost topology is proved.

Additional clues:

- `ABOX SOUNDBOOST_A/B/EN` were None/None/Off in an archived mixer dump; map
  their actual semantics before touching them.
- Read-only `Left DSP1 Protection cd PL_SPK_OUTPUT_POWER` and
  `Right DSP1 Protection cd L_SPK_OUTPUT_POWER` were zero in an idle snapshot;
  sample during active playback.
- `Right AMP SPK` maps to physical SPEAKER; `Left AMP SPK` maps to RECEIVER.
  `Right AMP PCM Gain` is the relevant volume element for the SPEAKER endpoint.

See `docs/beta-finalization/live/PWNAGE-40000-AUDIO-ROOT-CAUSE.md` for the full
source analysis and conditional kernel-driver lead.

## New diagnostic

Use `tools/s10plus/a33/nuxel-cs35l41-speaker-diag.sh` for read-only device-tree,
regmap, mixer, DAPM, DSP, PipeWire and PCM capture. Its optional watcher samples
the PCM while a separately initiated one-play test is running. It never plays
a sound or changes hardware state.

## Persistence status

Calliope firmware readiness, both protection DSP loads, RDMA1 routing, PipeWire
48 kHz sink selection and the boot cue readiness work are retained. The latest
speaker tests restored the existing route after each experiment. The kernel
build wrapper has been fixed to actually process its declared patch directory;
no CS35L41 output patch has been added yet because boost mode must first be
identified.

## Explicitly not done

- Physical speaker audibility remains unconfirmed/negative.
- No TWRP reflash, kernel flash, boot image flash or firmware-partition write.
- No external-boost sequence blindly applied.
- No amplifier protection or thermal-limit bypass.
- Headphone, USB-C audio and microphone tests remain separate.
