# SSP-05_12 — ROM First-Light Result

**Date:** 2026-11-22/23
**Status:** `ROM_GETVERSION_PASS = FALSE`

A genuine, authorized, bounded ROM probe was executed after the corrected
symmetric cold-cycle (patch 0028).  The boot-ROM did not answer GetVersion:
`rx=0`, `packets=0`, MISO `0xFF` (chip powered down via GPS_PWR_EN=0).

Root cause: the BCM47752 is held in power-down by `GPS_PWR_EN` (gpio-145)=0.
The rail cold-cycle (now correct) is necessary but not sufficient.

No synthetic/replayed success is claimed.  `ROM_GETVERSION_PASS` remains unmet.
