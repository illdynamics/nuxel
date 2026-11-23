# SSP-05_10 — NUXEL BOOT VERIFICATION (PLACEHOLDER)

**Date:** 2026-11-22 (Europe/Amsterdam)
**Status:** NOT YET RUN — BOOT flash has NOT been performed (awaiting owner authorization).

This report will be populated AFTER the authorized BOOT-only flash and the resulting
reboot. It must record one of the mandated outcomes:

- `BOOT_NUXEL = PASS` — Nuxel boots, kernel identity verified, SSH/systemd/display/
  input/network/storage all healthy, BOOT/DTB/DTBO identity confirmed.
- `BOOT_CANDIDATE_FAILED_RECOVERED` — candidate failed (return-to-TWRP / hang /
  bootloop), known-good BOOT restored, Nuxel healthy.
- `RECOVERY_BLOCKED` — safe recovery could not be completed.

## To be verified after a successful boot

1. SSH / management channel reachable (root@10.11.12.99 or established channel).
2. `uname -a` == `4.14.253-gf7194c1d15ed-dirty`.
3. systemd healthy (`systemctl is-system-running`).
4. Core display, input, networking, storage functional.
5. `/dev/block/sda14` hash == `9805d519b61c38a960158753679e1e2af0cf1783ce4f4c6e3c8b0ba6be5fbca7`.
6. sda12/sda13/sda15 hashes unchanged (dtb/dtbo/recovery baseline intact).
7. 0025 correction present in running kernel; BBD raw transport functional on
   `/dev/ttyBCM` + `/dev/bbd_sensor|bbd_control|bbd_patch`.
8. Corrected `--rom-probe` userspace executable present.
9. MCU power-management interface present; no service/transport ownership conflicts.
10. Read-only regulator/GPIO diagnostics captured; GNSS subsystem checked.

## Current record

`BOOT_NUXEL = NOT_RUN` — no flash authorized or performed. See
`SSP-05_10-BOOT-FLASH-RECEIPT.md` for the exact pending authorization request.

MCU power transition / GNSS rail / `GPS_PWR_EN` manipulation remain SEPARATELY
gated and are NOT authorized by this prompt (see section 9 of the mandate).
