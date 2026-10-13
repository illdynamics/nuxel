# G7 Power Snapdragon X9 LTE Modem — Status

The Qualcomm Snapdragon X9 LTE modem (integrated in SDM632 / msm8953) is NOT
ready for ModemManager in Nuxel Phase 1. There is no upstream MM plugin for
the X9 LTE modem interface on msm8953.

Phase 1 target: WiFi (WCN3680B / wcn36xx) only.
Phase 7 (stretch): Explore X9 LTE interface; implement custom MM plugin.

NEVER flash modemst1, modemst2, fsg, fsc, ddr — these hold per-unit IMEI
and radio calibration data.

---

## Protected-partition warnings (all Nuxel scripts)

The following partitions are **never** touched by any Nuxel flash/build
script on the G7 Power (denylist enforced in `boot/g7power/flash.sh` and
`firmware/g7power/install-firmware.sh`): `modemst1`, `modemst2`, `fsg`,
`fsc`, `ddr`, `persist`, `misc`. Writing to any of them can destroy IMEI,
baseband calibration, or the boot state and is not recoverable without
Motorola service tools.

## Status table

| Item                   | Phase 1 (current)                          | Phase 7 (stretch)                     |
|------------------------|--------------------------------------------|---------------------------------------|
| WiFi                   | ✅ primary connectivity (WCN3680B / wcn36xx)| —                                     |
| Voice / SMS / data     | ❌ not available (no MM plugin)             | Explore X9 LTE interface              |
| ModemManager           | ❌ no upstream plugin for X9 LTE on msm8953 | Implement custom MM plugin (stretch)  |
| `modem` partition      | ⛔ DO NOT flash                             | Only with explicit Phase 7 guidance   |
| `modemst1`/`modemst2`/`fsg`/`fsc`/`ddr` | ⛔ NEVER flash or wipe (IMEI/baseband) | ⛔ NEVER flash or wipe      |

## Related

* `docs/g7power-bringup.md` — full bring-up guide (Phase 0 → flash).
* `docs/g7power-device-inventory.md` — Phase 0 collection commands.
* `firmware/g7power/manifest.yml` — modem firmware entry is
  **DO NOT INSTALL** until Phase 7.
