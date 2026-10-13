# Nuxel S10+ PipeWire — Samsung Galaxy S10+ (beyond2lte)

Device-keyed PipeWire guidance for the S10+ (Exynos 9820, beyond2lte).

## Audio hardware (verified)

| Role  | Part                                   |
|-------|----------------------------------------|
| Codec | Cirrus Logic **CS47L93** (MADERA ASoC) |
| Amps  | **2x CS35L40** smart speaker amplifiers|

ALSA card name: **TBD** — obtain with `aplay -l` on the real device during
Phase 0 (`docs/s10plus-device-inventory.md`). Nothing here invents a card
name or a mixer value.

## Status

Phase 1 is bring-up: audio values are UNKNOWN until Phase 0. The CS47L93 card
must first enumerate (needs `madera` ASoC kernel support + `cs47l93-dsp1-*.wmfw`
DSP firmware — see `configs/s10plus/alsa-ucm/README.md`), then the ALSA UCM
profiles can be validated, and only then does a PipeWire device config make
sense.

## Safe default (placeholder, 48 kHz / 2ch stereo)

Until the real card is identified, a safe stereo 48 kHz clock default is used
(no card-specific routing):

```ini
context.properties = {
    default.clock.rate          = 48000
    default.clock.allowed-rates = [ 48000 ]
    default.clock.quantum       = 1024
}
```

## Required ALSA UCM profile path

The profiles in `configs/s10plus/alsa-ucm/SamsungBeyond2/` install to:

```
/usr/share/alsa/ucm2/SamsungBeyond2/SamsungBeyond2.conf
```

and are selected by card name once Phase 0 `aplay -l` identifies it. PipeWire
exposes the UCM devices automatically through the ALSA plugin once the UCM
profile is installed and selected.

## Install (after Phase 0 card identification)

```sh
sudo mkdir -p /etc/pipewire/pipewire.conf.d
sudo install -m0644 <generated 40-nuxel-s10plus.conf> \
    /etc/pipewire/pipewire.conf.d/40-nuxel-s10plus.conf
systemctl --user restart pipewire pipewire-pulse wireplumber
```

The generated fragment must be validated against the Phase 0 `aplay -l` /
`tinymix` capture before it is committed to this tree — no values are
invented beforehand.
