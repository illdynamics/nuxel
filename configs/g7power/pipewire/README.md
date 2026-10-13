# Nuxel G7 Power PipeWire — Motorola Moto G7 Power (ocean)

Device-keyed PipeWire guidance for the G7 Power (XT1955, SDM632 / msm8953,
ocean).

## Audio hardware (verified)

| Role  | Part                                    |
|-------|-----------------------------------------|
| Codec | Qualcomm **WCD9335** (cajon-v2) ASoC    |

ALSA card name: **TBD** — obtain with `aplay -l` on the real device during
Phase 0 (`docs/g7power-device-inventory.md`). Nothing here invents a card
name or a mixer value.

## Status

Phase 1 is bring-up: audio values are UNKNOWN until Phase 0. The WCD9335 card
must first enumerate (needs `CONFIG_SND_SOC_WCD9335=y` in the kernel — see
`configs/g7power/alsa-ucm/README.md`), then the ALSA UCM profiles can be
validated, and only then does a PipeWire device config make sense.

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

The profiles in `configs/g7power/alsa-ucm/WCD9335/` install to:

```
/usr/share/alsa/ucm2/WCD9335/WCD9335.conf
```

and are selected by card name once Phase 0 `aplay -l` identifies it. PipeWire
exposes the UCM devices automatically through the ALSA plugin once the UCM
profile is installed and selected.

## Install (after Phase 0 card identification)

```sh
sudo mkdir -p /etc/pipewire/pipewire.conf.d
sudo install -m0644 <generated 40-nuxel-g7power.conf> \
    /etc/pipewire/pipewire.conf.d/40-nuxel-g7power.conf
systemctl --user restart pipewire pipewire-pulse wireplumber
```

The generated fragment must be validated against the Phase 0 `aplay -l` /
`tinymix` capture before it is committed to this tree — no values are
invented beforehand.
