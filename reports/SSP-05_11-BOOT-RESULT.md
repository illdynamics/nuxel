# SSP-05_11 — BOOT Result

**Date:** 2026-11-22 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** Samsung Galaxy S10+ (SM-G975F / beyond2lte), serial R58M75KDB2X

## Result

**`BOOT_NUXEL = SUCCESS`**

The BOOT-only flush of candidate `9805d519...` to `/dev/block/sda14` was authorized
this session, executed, independently verified by post-write readback, and the device
booted normally into the intended Nuxel kernel.

## Write details

| Field | Value |
|---|---|
| Target | /dev/block/sda14 (by-name boot) |
| Source | evidence/pwnage-ssp-05_9/candidate-boot-0020-0023-0025.img |
| Candidate SHA-256 | 9805d519b61c38a960158753679e1e2af0cf1783ce4f4c6e3c8b0ba6be5fbca7 |
| Bytes written | 57,671,680 (14080 x 4096, rc=0) |
| Post-write readback sda14 | 9805d519... MATCH |
| sda12/sda13/sda15 | unchanged (abc9d45d/de3bc025/4cc71d62) |

## Boot verification

```
Linux WIN-CLIENT 4.14.253-gf7194c1d15ed-dirty #2 SMP PREEMPT Sun Nov 22 19:30:50 CET 2026 aarch64 GNU/Linux
```

- Correct running kernel identity: PASS
- Expected SSP patch presence (0020+0023+0025 symbols in kallsyms): PASS
- systemd running + management (SSH) reachable: PASS
- Display/touchscreen/storage/networking healthy: PASS
- No new critical kernel errors: PASS

## Post-boot read-only SSP checks

1. Deployed 0025 correction: mcu_power sysfs node present (value=1). PASS
2. Existing BBD raw transport: /dev/bbd_sensor|control|patch|urgent_patch + /dev/ttyBCM. PASS
3. Corrected userspace ROM probe: nuxel_bbd_tl.py / nuxel_bbd_host / nuxel_bbd_download present. PASS
4. Regulator state: vdd_mcu_1p8 state=enabled num_users=0 (read-only, not transitioned). OBSERVED
5. Kernel init + transport ownership: single-owner BBD callbacks present. PASS
6. Service ordering: nuxel-* services running. PASS
7. GNSS/other subsystems: healthy; ROM first-light NOT yet probed (power gate).

## Outcome

**`BOOT_DEPLOYED_POWER_TRIAL_PENDING`** — Nuxel boots with 0025; ROM first light
remains unverified pending a separately-authorized, bounded MCU power transition.
