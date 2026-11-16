# Firmware inventory — no binary firmware included

The repository archive does **not** contain a verified, model-matched Samsung Shannon S5000AP CP image that can be used by a native loader. It also does not contain a validated replacement for Samsung `cbd` or the exact G975F CP boot transaction.

No firmware binary has been generated: a Shannon CP image is device/vendor firmware, not something that can be synthesized from an interface description or generic Exynos source. Do not substitute Exynos 5500, Exynos 9825, Pixel, Qualcomm, Calliope audio firmware, or another region/model image.

Required source provenance before any loader implementation:

- exact SM-G975F / `beyond2lte` firmware generation and matching CSC/build identity;
- official/signed OEM firmware package or other owner-approved lawful source;
- CP image identity, container format, section table and hashes;
- comparison against the exact 4.14.253 kernel's `modem_firmware` ABI and matching Samsung loader behavior;
- legal/re-distribution review. Do not place proprietary binaries in Nuxel source control or this pack.

Strict invariants:

- never write/flash the modem partition;
- never read/write EFS, EFSG, SEC_EFS, persist, NV, calibration, carrier, or IMEI storage;
- never initialise, erase, restore, clone, or “repair” per-device radio data;
- never store/print IMSI, ICCID, IMEI, PIN, PUK, MSISDN or APN credentials;
- if the exact firmware source or boot protocol is unavailable, stop at a documented blocker rather than guessing.
