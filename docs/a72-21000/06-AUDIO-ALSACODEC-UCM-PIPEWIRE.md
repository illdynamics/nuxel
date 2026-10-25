# NUXEL A72 / 21000 — 06-AUDIO (live re-measured with real tools)

Updated after alsa-utils/alsa-ucm/pipewire/wireplumber were installed via dnf5.

## ALSA card truth (fresh)
- `cat /proc/asound/cards`: `beyond-madera` (0), `abox_vdma` (1), `abox_dump` (2).
- `aplay -l`: RDMA0-11 playback, WDMA0-7 capture, VTS-Trigger/Record, DP Audio.
- `amixer -c 0 scontrols`: 813 controls. Present codec/DSP/ABOX controls include
  `DSP1 Firmware`, `DSP1 Preload`, `DSP1 Rate`, `ABOX DSIF SPK`, AIF1/2TX routing.

## Root cause of NO speaker sound (proven this run, not assumed)
1. `dmesg` (recurring, every ABox runtime resume):
   - `samsung-abox-core 18c55000.abox-core: calliope_sram.bin isn't loaded yet`
   - `Direct firmware load for calliope_sram.bin failed with error -2`
2. `aplay -D hw:0,0` (and `plughw:0,0`) on a valid 44100 Hz S16 WAV fails:
   - `Unable to install hw params` (rc=1), then
   - `beyond-madera sound: beyond_dai_ops_hw_free: RDMA0-0`
   The ABox DSP cannot configure the PCM engine without `calliope_sram.bin`.
3. Cirrus CS47L93 codec DSP (`cs47l93-dsp{,-1,-2}.wmfw/.bin`) and CS35L40 amp DSP
   (`cs35l40-dsp1/2.wmfw/.bin`) also remain absent (05-FIRMWARE audit).

Conclusion: speaker/headphone output is **BLOCKED_FIRMWARE** at the ABox DSP +
Cirrus codec/amp layer. Installing PipeWire/alsa-utils cannot fix absent
Samsung/Cirrus firmware; this is documented as a firmware boundary, not a missing
userspace package.

## UCM placement (resolved)
`alsa-ucm` package now installs upstream UCM profiles under
`/usr/share/alsa/ucm2/`. The repo's historical `configs/s10plus/alsa-ucm/
SamsungBeyond2/HiFi.conf` was never the live card alias. The live card is
`beyond-madera`; a matching `ucm2/beyond-madera/HiFi.conf` does not exist and
cannot be authored safely without the codec/amp DSP mixer semantics. This is a
separate (firmware-dependent) gap, not simply a copy-path mistake.

## PipeWire / WirePlumber (installed)
pipewire 1.4.11, wireplumber 0.5.14, pipewire-alsa, pipewire-pulseaudio installed
(signed Fedora 43 aarch64, gpgcheck=1). The Nuxel root session has no session
D-Bus, so `systemctl --user` cannot start them; they can only be launched
directly. No sink can appear until the ALSA card can install hw params (blocked
by calliope_sram). PipeWire daemons were NOT left running.

## Media decode vs audible output
`mpv --no-video --ao=null /tmp/nuxel-test-tone.wav` decodes the 44100 Hz S16 WAV
and exits cleanly (AO:null, End of file) — **decode/runtime PASS**, audible
output still firmware-blocked. This separation is reported honestly (no fake
"audio fixed").
