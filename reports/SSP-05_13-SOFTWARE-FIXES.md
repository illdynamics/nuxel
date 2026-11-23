# SSP-05_13 — Software Fixes (defects identified, correction prepared)

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 1. Defect #1 — `regulator_force_enable()` corrupts `open_count` (0028)

**File:** `drivers/regulator/core.c` (introduced by patch 0028)

```c
if (rdev->supply)
        while (rdev->open_count--)
                regulator_enable(rdev->supply);
```

**Defect:** drains `rdev->open_count` to zero and re-enables the parent supply
with incorrect ordering/count.  Breaks the consumer-handle invariant and can
trigger `WARN_ON(rdev->open_count)` at teardown.

**Correction (prepared as patch 0029):** remove the trailing loop; keep only
the `_regulator_do_enable(rdev)` call under `rdev->mutex`.

**Status:** patch file written
`kernel/s10plus/patches/0029-nuxel-ssp-regulator-force-enable-open-count-fix.patch`.
NOT deployed (no flash authorization; see PHYSICAL-TRIAL-DECISION.md).

## 2. Defect #2 — `regulator_force_enable()` lacks notifier symmetry (0028)

**Defect:** `regulator_force_disable()` fires
`REGULATOR_EVENT_FORCE_DISABLE|PRE_DISABLE|DISABLE`; the symmetric
`regulator_force_enable()` fires none of `PRE_ENABLE|ENABLE`.  Consumers
subscribed to enable/disable notifiers will not observe the re-enable.

**Recommendation:** if the narrow recovery path needs notifier parity, call
`_notifier_call_chain(rdev, REGULATOR_EVENT_PRE_ENABLE/ENABLE, NULL)` around
`_regulator_do_enable()`.  This is documented but deliberately NOT folded into
0029 to keep the correction minimal; it can be a follow-up if a subscriber is
identified that depends on it.

## 3. Defect #3 — stale build tree hides 0028 (environmental, not code)

**Finding:** the local kernel Image in `.build/out` (`arch/arm64/boot/Image`,
SHA-256 `8dae55e28a0ce5b173860d0dc8c52a1022a0cedcc214d009fc8d4fd1108dfdcb`,
built 2026-11-22 19:31) predates patch 0028 (mtime 2026-11-22 23:26) and its
`System.map`/`Module.symvers` contain **only** `regulator_force_disable`, no
`regulator_force_enable`.

**Implication:** the current BOOT image with 0028 (`760c0e44...`) was built from
a source tree not present locally; `/Volumes/kernelbuild/src` is unmounted.
The 0029 correction therefore **cannot be compile-validated in this session**
without re-mounting the source volume and rebuilding.

**Recommendation:** re-mount `/Volumes/kernelbuild`, rebuild with 0028→0029,
then run a full BOOT preflight before any flash (per safety directive).

## 4. What was intentionally NOT changed

- No direct GPIO writes to `GPS_PWR_EN`.
- No DTB/DTBO modification.
- No firmware MemoryWrite / app-start.
- No broad regulator-core change beyond the narrowly-scoped 0029 correction.
- No invented timing constants.

## 5. Offline test receipts

- `grep`: `GPS_PWR_EN` appears only in `bcm_gps_spi.c:1155-1225` (probe), never
  asserted HIGH anywhere in `drivers/sensorhub/`.
- `git apply --check` of 0029 could not run cleanly against a source tree that
  lacks 0028 (the 0028 hunk is absent from `src.polluted.case-insensitive`);
  the correction was written against the 0028 patch content and upstream
  `core.c` read directly.
- `System.map` / `Module.symvers` inspection confirms the local Image is
  pre-0028 (no `regulator_force_enable` symbol).

## 6. Verification outstanding

- Compile-check 0029 after re-mounting the source volume.
- Confirm the deployed on-device kernel's `regulator_force_enable` matches the
  0028 patch before deciding whether a re-flash is needed at all.
