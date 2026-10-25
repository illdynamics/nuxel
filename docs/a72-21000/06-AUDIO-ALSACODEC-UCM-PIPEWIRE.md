# NUXEL A72 / 21000 — 06-AUDIO-ALSACODEC-UCM-PIPEWIRE

## Exact chain (fresh)
Exynos ABox (`abox@18c50000`, needs `calliope_sram.bin`) → ASoC machine
`samsung,beyond-madera` → Cirrus CS47L93 (needs `cs47l93-dsp*.wmfw/.bin`) →
2× CS35L40 amps (need `cs35l40-dsp*.wmfw/.bin`). ALSA cards: `beyond-madera`(0),
`abox_vdma`(1), `abox_dump`(2). PCM: RDMA0-11 playback, WDMA0-7 capture, DP Audio.

## Root cause of "no sound" (multi-layer, each independently blocking)
1. ABox calliope DSP firmware absent (journal: `calliope_sram.bin ... error -2`).
2. Cirrus CS47L93 codec DSP absent (`nuxelctl audio status` → BLOCKED_FIRMWARE).
3. CS35L40 amp DSP absent.
4. UCM profile: repo has `configs/s10plus/alsa-ucm/SamsungBeyond2/*` but the card
   name is `beyond-madera`, so the correct install root is
   `/usr/share/alsa/ucm2/beyond-madera/` — NOT `SamsungBeyond2/`. The repo profile
   is also an explicit STUB (empty EnableSequence; "no invented mixer values"), so
   even a correct copy would not power the amp path.
5. No audio server: PipeWire / WirePlumber absent (only `pulseaudio-libs` client).
6. No alsa-utils (`aplay`/`amixer`/`alsaucm` absent).

## UCM card-ID mismatch resolution
- Actual card ID (from `/proc/asound/cards`) = `beyond-madera`.
- `configs/s10plus/alsa-ucm/SamsungBeyond2/` is the historical wrong alias.
- Correct action (later, after firmware exists): generate a real `beyond-madera`
  UCM2 profile from real mixer capture (owner TWRP `tinymix` or a safe on-device
  `amixer -c0 contents` once alsa-utils is installed), never guessed gain values.

## Userspace recovery path (needs dnf5 first — approval-gated)
`alsa-utils`, `alsa-ucm`, `pipewire`, `pipewire-alsa`, `wireplumber` (signed
Fedora 43 aarch64). These are USERSpace packages; they do NOT substitute for the
missing DSP firmware. Install order: dnf5 bootstrap → alsa-utils (diagnose) →
pipewire/wireplumber (server) → then a safe low-volume ALSA/PipeWire signal test,
human-observed, never a stream return-code alone.

## Honest status
- Speaker audibility: BLOCKED_FIRMWARE (calliope_sram + cs47l93/cs35l40 DSP).
- USB-C DAC / BT speaker routes: independent, gated on BlueZ/pipewire + an accessory.
