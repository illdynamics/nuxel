# Nuxel G7 Power ALSA UCM — Motorola Moto G7 Power (ocean)

Device-keyed ALSA UCM2 configuration for the Motorola Moto G7 Power (XT1955,
SDM632 / msm8953, codename ocean). Everything under this directory is G7
Power-specific; nothing here applies to any other Nuxel target.

## Audio topology (verified hardware facts)

| Role  | Part                                   | Notes                            |
|-------|----------------------------------------|----------------------------------|
| Codec | Qualcomm **WCD9335** (cajon-v2) ASoC   | Main audio codec on the AP       |
| SoC   | Qualcomm SDM632 (msm8953 family)       | Audio subsystem in the AP        |

ALSA card name: **TBD** — obtain from the real device with `aplay -l` or
`cat /proc/asound/cards` during Phase 0 (see
`docs/g7power-device-inventory.md`). No card name or mixer value is invented
in this tree.

## Reference UCM configs

* Reference the **production-tested WCD9335 UCM for ocean / sdm632** from
  **https://github.com/msm8953-mainline/alsa-ucm-conf** — this is the
  starting point for the real profiles. Do not hand-roll mixer routing from
  other devices (mustang / s10plus use completely different codecs:
  Exynos/CS47L93 and Pixel/Exynos-modem audio — never reuse those).

## Kernel requirements

* WCD9335 (cajon-v2) requires **`CONFIG_SND_SOC_WCD9335=y`** in the kernel
  (see `kernel/g7power/defconfig`); until that is present the card will not
  enumerate and no UCM routing can be validated.

## UCM routing — UNKNOWN until Phase 0

UCM routing **must be built from real device `tinymix` output captured
during Phase 0**. No mixer control names or values are invented in this tree
— the `WCD9335/` profiles below are explicit stubs with empty
enable/disable sequences until the Phase 0 capture exists.

## Install layout

Profiles install to `/usr/share/alsa/ucm2/WCD9335/`:

```
WCD9335/
├── WCD9335.conf   # master UCM file (Syntax 2) linking the use cases
└── HiFi.conf      # HiFi use case (stub)
```

## Files in this directory

* `WCD9335/WCD9335.conf` — master UCM file (Syntax 2) linking the HiFi use
  case via `File "HiFi.conf"`; card name TBD-from-`aplay -l` noted inside.
* `WCD9335/HiFi.conf` — stub HiFi profile for the WCD9335 cajon-v2 codec
  with empty sequences; every mixer value stays UNKNOWN until Phase 0.

## Related

* `configs/g7power/pipewire/` and `configs/g7power/wireplumber/` — user-space
  audio stack, keyed off the same Phase 0 card name.
* `firmware/g7power/manifest.yml` — audio DSP firmware entry (UNKNOWN until
  Phase 0 inventory).
