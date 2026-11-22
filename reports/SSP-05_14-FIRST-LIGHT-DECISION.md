# SSP-05_14 — First-Light Decision

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

The S0→S1 transition (assert GPS_PWR_EN = gpg0-2) is NOT authorized by the
BOOT-flash mandate (Section 0.2 / Section 10).  It requires separate owner
approval after the safety evidence enumerated in SSP-05_13-PHYSICAL-TRIAL-DECISION.md
is produced:

1. Broadcom BCM47752 datasheet: GPS_PWR_EN assertion sequence + post-power timing
   (logic-vs-RF domain separation).
2. Samsung gpsd/lhd disassembly: exact assertion order, post-power delay, RF
   de-energisation step.
3. Owner confirmation that energising the GNSS domain (logic+RF) is acceptable.

Until ≥1 of these is available, the correct record is: do NOT perform the trial.
This session performed NO GPS_PWR_EN assertion and NO new regulator transition
(the deployed 0029 was validated read-only).
