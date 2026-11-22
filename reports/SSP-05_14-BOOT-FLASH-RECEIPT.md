# SSP-05_14 — BOOT Flash Receipt

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X

## Flash (authorized BOOT-only)

| Field | Value |
|---|---|
| Authorization | Owner Section 0.1 (guarded BOOT-only, single write) |
| Target | /dev/block/sda14 (by-name: boot) |
| Source (on-device) | /tmp/boot-candidate-0029.img |
| Candidate SHA-256 | 1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599 |
| On-device pre-write hash | 1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599 (MATCH) |
| Bytes written | 57,671,680 (14080 x 4096, rc=0) |
| Pre-flash boot | 760c0e44 (0028) |

## Post-write independent readback

| Partition | SHA-256 | Result |
|---|---|---|
| boot sda14 | 1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599 | MATCH candidate (FLASHED) |
| dtb sda12 | abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780 | unchanged |
| dtbo sda13 | de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23 | unchanged |
| recovery sda15 | 4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87 | unchanged |

## Rollback preserved

- host:/tmp/nuxel-boot/boot-0028-current.img = 760c0e44
- host:evidence/pwnage-ssp-05_12/boot-0028-candidate.img = 760c0e44
- device:/cache/nuxel-ssp-rollback/boot-sda14-known-good-760c0e44.img = 760c0e44
- device:/cache/nuxel-ssp-rollback/boot-sda14-known-good-9805d519.img = 9805d519

## Next

`adb reboot` -> normal Nuxel boot expected (TWRP agreement requirement).
