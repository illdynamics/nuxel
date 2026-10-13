# Nuxel S10+ WirePlumber — Samsung Galaxy S10+ (beyond2lte)

Device-keyed WirePlumber guidance for the S10+ (Exynos 9820, beyond2lte).

## Audio context (same as configs/s10plus/pipewire/README.md)

| Role  | Part                                   |
|-------|----------------------------------------|
| Codec | Cirrus Logic **CS47L93** (MADERA ASoC) |
| Amps  | **2x CS35L40** smart speaker amplifiers|

ALSA card name: **TBD** from real device `aplay -l` (Phase 0). Safe default
placeholder: 48000 Hz, 2ch stereo. No values are invented.

## UCM profile dependency

WirePlumber's ALSA monitor exposes the UCM2 profiles selected from:

```
/usr/share/alsa/ucm2/SamsungBeyond2/SamsungBeyond2.conf
```

Once the Phase 0 card name is known and the UCM HiFi profile is confirmed,
add an ALSA-monitor rule that matches the S10+ card name and pins the default
node properties (e.g. `audio.position = "FL,FR"`, `node.description` with the
S10+ card) to the HiFi UCM device. Until then there is nothing
device-specific to configure and no rule is shipped.

## After Phase 0

1. Identify the card name (`aplay -l`, `/proc/asound/cards`).
2. Install + validate the UCM profiles (see `configs/s10plus/alsa-ucm/`).
3. Add the ALSA-monitor rule here, keyed to the S10+ card name, following the
   standard WirePlumber rule shape (`rule = { matches = ..., apply_properties
   = ... }` + `table.insert(alsa_monitor.rules, rule)`).
4. Re-run `wpctl status` on the device to confirm the S10+ card and UCM
   devices are visible before committing the rule.

## Install

```sh
sudo mkdir -p /etc/wireplumber/wireplumber.conf.d
sudo install -m0644 <generated 40-nuxel-s10plus.lua> \
    /etc/wireplumber/wireplumber.conf.d/40-nuxel-s10plus.lua
systemctl --user restart wireplumber
```
