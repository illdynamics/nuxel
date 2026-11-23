# SSP-0025 — Prompt 06 Readiness Assessment (Prompt 05_8 §9/§10)

**Agent:** DeepSeek-V4-Pro-Thinking
**Date:** 2026-11-22 (Europe/Amsterdam)

---

## Final decision

**BLOCKED_PREFLIGHT**

---

## Why (concise, evidence-backed)

The prompt's completion standard is unambiguous: success requires an *independently
verified, genuine ROM GetVersion while preserving the Nuxel boot/recovery baseline*.
That requires a genuine MCU cold power-cycle (the 0025 `regulator_force_disable`
correction), which requires a **deployed 0025 kernel** (BOOT-only flash), which requires
a **successful kernel build + full preflight**.

The build/preflight did **not** pass. Specifically:

1. **Patch 0025 is correct and compiles** — verified in source and via `ssp_sysfs.o`
   (contains `regulator_force_disable`). This is NOT the blocker.
2. **Patch 0027 is un-linkable** — `nuxel_bbd_patch_bytes` is `extern`-declared and
   called but never defined (`undefined reference` at `vmlinux` link). Real SSP defect.
3. **The macOS/GCC-15 host cannot complete the full vendor-tree `Image.gz` build** —
   global `-Werror` (Makefile:428) promotes pre-existing `-Wformat`/`-Wunused-variable`
   warnings in *unrelated* Samsung SoC/display drivers (`exynos-ppmpu.c`, DPU20) to
   errors; plus host `<elf.h>`/`<endian.h>` absence (shimmed by the build script).

Because `Image.gz` cannot be produced, no BOOT candidate exists, and the mandatory
`successful kernel build` gate (§3) fails. Any mandatory FAIL/BLOCKED gate → **NO FLASH**
per §3. Hence:

**BLOCKED_PREFLIGHT** — one or more kernel build / BOOT packaging / rollback requirements
failed.

---

## Status of the other possible decisions (why NOT these)

- **READY_FOR_06**: No. No genuine ROM GetVersion was obtained (would require the deployed
  0025 kernel + authorized power cycle, both absent).
- **AWAITING_BOOT_FLASH_AUTHORIZATION**: No. This is only reachable *after* preflight
  passes; preflight failed.
- **AWAITING_POWER_TRIAL_AUTHORIZATION**: No. Requires the corrected kernel already
  deployed and healthy; it is not deployed.
- **BLOCKED_POWER_SAFETY**: Not yet the *final* decision, though §1's shared-rail rule
  does independently forbid *automatic* rail cycling. The dominant blocker at this point
  is the build/preflight failure, which precedes the power-safety question.
- **ROM_FIRST_LIGHT_FAILED**: No. No authorized physical trial was run to fail.

---

## What must happen before Prompt 06 (ordered)

1. **Repair 0027** (implement `nuxel_bbd_patch_bytes`) — or document a 0025-only build
   that explicitly excludes 0027 and passes the build-script's SSP gate.
2. **Resolve the toolchain blocker** (GCC 4.9/8-era `aarch64-linux-android-` toolchain,
   or neutralize vendor `-Werror` for unrelated drivers) to produce `Image.gz`.
3. **Package the BOOT candidate** via `pack-ssp-boot.py`; verify donor + rollback.
4. **Separately obtain**: (a) BOOT-only flash authorization; (b) bounded MCU cold-cycle
   authorization.
5. Only then run `--rom-probe` and require a genuine framed/CRC'd RPC-0 GetVersion.
6. Verify Nuxel boot + recovery baseline + DTB/DTBO unchanged throughout.

---

## Deliverables produced this prompt

- `reports/SSP-0025-KERNEL-RECONCILIATION.md`
- `reports/SSP-0025-BOOT-PREFLIGHT.json`
- `reports/SSP-0025-POWER-SAFETY.md`
- `reports/SSP-0025-ROM-FIRST-LIGHT.md`
- `reports/SSP-0025-KERNEL-SOURCE-MANIFEST.json`
- `reports/SSP-0025-PROMPT06-READINESS.md` (this file)

---

## Truthfulness attestation

No `ESW:READY`, WHOAMI, accelerometer, gyroscope, ROM identity, or GetVersion value was
synthesized. No BOOT flash, regulator force-disable, power transition, or ROM probe was
performed this prompt. The device remains bootable on `4.14.253-gf7194c1d15ed-dirty`
with the 0020+0023 passthrough and no 0025/0027 deployment.
