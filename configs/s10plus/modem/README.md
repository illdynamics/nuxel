# S10+ Shannon LTE Modem — Status

The Samsung Shannon LTE modem (integrated into Exynos 9820) is NOT ready for
ModemManager in Nuxel Phase 1. There is no upstream ModemManager plugin for
the Shannon LTE modem interface.

Phase 1 target: WiFi only. No voice/SMS/data via cellular modem.
Phase 7 (stretch goal): Explore Shannon LTE interface; implement MM plugin.

The modem CP firmware lives in the `modem` partition. DO NOT flash or modify
the modem partition without explicit Phase 7 guidance.

The `efs` and `efsg` partitions hold per-unit IMEI and baseband calibration.
NEVER flash or wipe these partitions.

---

## Protected-partition warnings (all Nuxel scripts)

The following partitions are **never** touched by any Nuxel flash/build
script on the S10+ (denylist in `boot/s10plus/flash.sh`): `efs`, `efsg`,
`persist`, `param`, `up_param`, `steady`, `keystorage`, `carrier`,
`cp_debug`, `misc`. Writing to any of them can destroy IMEI, baseband
calibration, or the boot state and is not recoverable without Samsung
service tools.

## Status table

| Item             | Phase 1 (current)                        | Phase 7 (stretch)                    |
|------------------|------------------------------------------|--------------------------------------|
| WiFi             | ✅ primary connectivity                   | —                                    |
| Voice / SMS/data | ❌ not available (no MM plugin)           | Explore Shannon LTE interface        |
| ModemManager     | ❌ no upstream plugin for Shannon LTE     | Implement MM plugin (stretch)        |
| `modem` partition| ⛔ DO NOT flash                           | Only with explicit Phase 7 guidance  |
| `efs`/`efsg`     | ⛔ NEVER flash or wipe (IMEI/baseband)    | ⛔ NEVER flash or wipe               |

## Related

* `docs/s10plus-bringup.md` — full bring-up guide (Phase 0 → flash).
* `docs/s10plus-device-inventory.md` — Phase 0 collection commands.
* `firmware/s10plus/manifest.yml` — modem firmware entry is
  **DO NOT INSTALL** until Phase 7.
