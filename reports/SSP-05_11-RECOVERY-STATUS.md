# SSP-05_11 — Recovery Status

**Date:** 2026-11-22 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Status:** `ROLLBACK_READY = TRUE` (recovery baseline preserved post-flash)

## Known-good BOOT (rollback source)

- SHA-256: `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c`
- Size: 57,671,680 B

## Copy inventory (re-verified BEFORE flash)

| # | Location | Storage | SHA-256 | Verified |
|---|---|---|---|---|
| 1 | /tmp/nuxel-ssp-preflight/boot-sda14-fresh.img | host fs | 0e6aa34c... | YES |
| 2 | /data/media/nuxel-boot/boot-sda14-known-good-0e6aa34c-20261122.img | sda31 | 0e6aa34c... | YES |
| 3 | /cache/nuxel-ssp-rollback/boot-sda14-known-good.img | sda28 | 0e6aa34c... | YES |

All three copies byte-verified from their own endpoints before the flash. Device
copies are TWRP-accessible via direct ext4 ro mounts (sda31, sda28). Host copy
confirmed present at /tmp/nuxel-ssp-preflight/.

## Immutable baseline manifest (cache, unchanged)

`/cache/nuxel-ssp-rollback/immutable-hashes.sha256` records dtb/dtbo/recovery
baselines (abc9d45d / de3bc025 / 4cc71d62), which were re-verified unchanged
after the flash.

## Rollback procedure (use ONLY if a later boot regresses)

1. Re-enter TWRP (recovery sda15 unchanged, TWRP 3.7.0_9-2).
2. Mount sda31 or sda28 read-only.
3. `dd if=<known-good.img> of=/dev/block/sda14 bs=4096`
4. `sync`
5. Read back sda14; sha256sum must equal `0e6aa34c...`.
6. Reboot normal; confirm Nuxel boots.

Never write DTB, DTBO, recovery, bootloader, or unrelated partitions.

## Status

`ROLLBACK_READY = TRUE`
