# Nuxel S10+ audio — current status (2026-10-31, v0.7.4-beta)

Device: Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820
Userspace: Fedora 43 aarch64, PipeWire + WirePlumber

## Verdict

**The built-in speaker is audible and owner-confirmed.** This supersedes the
earlier "digital path verified, speaker silent" verdict. The PWNAGE-43000
experiments below tested the wrong variable (ABOX Sound Type, PCM Source and
sink level); the actual fault was the CS35L41 PLL reference.

The owner-confirmed fix (PWNAGE-40000, 2026-10-30) is applied by
`nuxel-audio-route.sh`: the device tree programs `ampclk=6.144 MHz`, but ABOX
UAIF1 clocks both amplifiers at 1.536 MHz (16-bit stereo 48 kHz), so the amps
were locked to the wrong reference. On both amps (`0x40`, `0x41`):
`SP_RATE_CTRL 0x4804=0x1b`, `PLL_CLK_CTRL 0x2c04=0x370`,
`AMP_DIG_VOL_CTRL 0x6000=0x8000`, `AMP_OUT_MUTE 0x2024=0x0`.

The durable path is the driver cache, because `cs35l41_pcm_mute(1)` on
`hw_free` rewrites `0x6000`/`0x2024` after every stream:
`Left/Right Digital PCM Volume = 817` (→ `0x8000`, 0 dB) and
`Left/Right AMP Mute = Unmuted`. `cs35l41_pcm_mute(0)` re-applies them on the
next playback.

The 366 ms cue is protected by `nuxel-audio-warmup`, which plays an inaudible
8 s 48 kHz stream at volume 0.0, waits for DAPM `SPEAKER=On`, re-applies the
cache/registers and only then lets the caller play the real POW.

**Owner confirmations (Notes title = reply channel):** `works` at 21:56Z
(manual warm-up + POW), 21:58Z (production volume cue), 22:00Z (Settings Test
Audio), 22:05Z (after full reboot) and 22:06Z (frozen helper build).

**Volume policy:** ceiling 100 %, first-boot default 50 %, `softvol max_dB=0.0`.

**Honest limit:** the raw I2C writer `/usr/local/bin/nuxel-cs35.py` is a
device-only artifact. A fresh image logs that the raw patch was not applied and
uses the driver-cache path.

### Historical record: PWNAGE-43000 experiments (all measured silent)

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
