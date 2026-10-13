# Nuxel G7 Power WirePlumber — Motorola Moto G7 Power (ocean)

Device-keyed WirePlumber guidance for the G7 Power (XT1955, SDM632 / msm8953,
ocean).

## Audio context (same as configs/g7power/pipewire/README.md)

| Role  | Part                                    |
|-------|-----------------------------------------|
| Codec | Qualcomm **WCD9335** (cajon-v2) ASoC    |

ALSA card name: **TBD** from real device `aplay -l` (Phase 0). Safe default
placeholder: 48000 Hz, 2ch stereo. No values are invented.

## UCM profile dependency

WirePlumber's ALSA monitor exposes the UCM2 profiles selected from:

```
/usr/share/alsa/ucm2/WCD9335/WCD9335.conf
```

Once the Phase 0 card name is known and the UCM HiFi profile is confirmed,
add an ALSA-monitor rule that matches the G7 Power card name and pins the
default node properties (e.g. `audio.position = "FL,FR"`,
`node.description` with the G7 Power card) to the HiFi UCM device. Until then
there is nothing device-specific to configure and no rule is shipped.

## After Phase 0

1. Identify the card name (`aplay -l`, `/proc/asound/cards`).
2. Install + validate the UCM profiles (see `configs/g7power/alsa-ucm/`).
3. Add the ALSA-monitor rule here, keyed to the G7 Power card name, following
   the standard WirePlumber rule shape (`rule = { matches = ...,
   apply_properties = ... }` + `table.insert(alsa_monitor.rules, rule)`).
4. Re-run `wpctl status` on the device to confirm the WCD9335 card and UCM
   devices are visible before committing the rule.

## Install

```sh
sudo mkdir -p /etc/wireplumber/wireplumber.conf.d
sudo install -m0644 <generated 40-nuxel-g7power.lua> \
    /etc/wireplumber/wireplumber.conf.d/40-nuxel-g7power.lua
systemctl --user restart wireplumber
```
