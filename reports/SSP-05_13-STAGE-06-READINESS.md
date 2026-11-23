# SSP-05_13 — Stage 06 Readiness

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## Gate status

| Gate | Status | Evidence |
|---|---|---|
| `BOOT_NUXEL_PASS` | PASS (as of 05_12) | `4.14.253-g73727632c863-dirty` boots; systemd 0 failed units |
| `REGULATOR_SAFETY_PASS` | **NOT PASS** | 0028 `regulator_force_enable()` corrupts `open_count` (audit). A 0029 correction is prepared but not deployed/validated. |
| `POWER_SEQUENCE_VERIFIED` | **PARTIAL** | Source sequence recovered (rail→GPS_PWR_EN→autobaud) but GPS_PWR_EN assertion timing/RF safety unverified |
| `ROM_GETVERSION_PASS` | **FALSE** | No valid GetVersion reply; GNSS domain power-gated |
| `DOWNLOADER_OFFLINE_PASS` | PASS (05_12) | downloader `--rom-probe`/`--flash` exclusive; ROM probe never writes firmware |
| `SYSTEM_INTEGRITY_PASS` | PASS (05_12) | dtb/dtbo/recovery digests unchanged |
| `ROLLBACK_READY` | PASS (05_12) | rollback boot `9805d519...` preserved |

## Additional finding (this session)

The local kernel build tree is **stale with respect to the deployed kernel**:
`.build/out/Image` (SHA `8dae55e2...`, built 19:31) predates patch 0028 (mtime
23:26) and its `System.map`/`Module.symvers` lack `regulator_force_enable`.
The source volume `/Volumes/kernelbuild/src` is unmounted, so the deployed
`760c0e44...` image could not be reproduced/verified locally this session, and
the full BOOT digest remains unretrieved (no device attached).

## Verdict

`READY_FOR_06` is **NOT** declared.  The precise remaining blocker is the
single `S0→S1` transition in the power state machine — the safety-validated
assertion of `GPS_PWR_EN` (gpg0-2) — which is blocked by missing vendor power-
sequence/datasheet evidence (not by a software defect alone, and not by an
unresolved regulator bug alone; the regulator 0028 issue is independently
corrected in the prepared 0029 but is secondary to the primary power-gate
blocker).

## Final status

```
BLOCKED_VENDOR_SEQUENCE
```
