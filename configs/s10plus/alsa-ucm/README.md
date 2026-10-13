# Nuxel S10+ ALSA UCM — Samsung Galaxy S10+ (beyond2lte)

Device-keyed ALSA UCM2 configuration for the Samsung Galaxy S10+ (Exynos 9820,
codename beyond2lte). Everything under this directory is S10+-specific; nothing
here applies to any other Nuxel target.

## Audio topology (verified hardware facts)

| Role    | Part                                       | Notes                              |
|---------|--------------------------------------------|------------------------------------|
| Codec   | Cirrus Logic **CS47L93** (MADERA ASoC)     | Main audio codec on the AP         |
| Amps    | **2x CS35L40** smart speaker amplifiers    | I2S/TDM to the CS47L93             |
| SoC     | Samsung Exynos 9820                        | Audio subsystem in the AP          |

ALSA card name: **TBD** — obtain from the real device with `aplay -l` during
Phase 0 (see `docs/s10plus-device-inventory.md`). No card name or mixer value
is invented in this tree.

## DSP firmware requirements

* The CS47L93 MADERA codec requires `madera` ASoC kernel support and its DSP
  firmware loaded via **`cs47l93-dsp1-*.wmfw`** files.
* The CS35L40 smart amplifiers require **`cs35l40-dsp*.wmfw`** firmware.

Both firmware families ship in the stock vendor image and must be collected
during Phase 0 inventory / firmware extraction (see
`firmware/s10plus/manifest.yml` and `docs/s10plus-device-inventory.md`).
Until those blobs are collected and installed, the codec DSP will not
enumerate correctly and no real UCM routing can be validated.

## UCM routing — UNKNOWN until Phase 0

UCM routing **must be built from real device `tinymix` output captured via
TWRP** during Phase 0. No mixer control names or values are invented in this
tree — the `SamsungBeyond2/` profiles below are explicit stubs with empty
enable/disable sequences until the Phase 0 capture exists.

## Reference

* **postmarketOS UCM2** for madera-family devices is the starting point for
  the real profiles (https://wiki.postmarketos.org/wiki/Cirrus_CS47L93 and
  the pmOS `postmarketos-audio`/UCM2 packaging).
* alsa-lib `alsaucm` / `alsactl` for validation once the card exists.
* `aplay -l`, `tinymix` (TWRP), `/proc/asound/cards` for card discovery.

## Install layout

Profiles install to `/usr/share/alsa/ucm2/SamsungBeyond2/`:

```
SamsungBeyond2/
├── SamsungBeyond2.conf   # master UCM file linking the use cases
└── HiFi.conf             # HiFi use case (stub)
```

## Files in this directory

* `SamsungBeyond2/SamsungBeyond2.conf` — master UCM file (Syntax 2) linking
  the HiFi use case; card name TBD-from-`aplay -l` noted inside.
* `SamsungBeyond2/HiFi.conf` — stub HiFi profile for the CS47L93 MADERA codec
  with empty sequences; every mixer value stays UNKNOWN until Phase 0.
