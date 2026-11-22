# Prompt 01 current status — 2026-11-22

The repository includes the patched offline guardrail implementation described
in `reports/camera-01-dt-gate.md`. The Master Contract remains binding.

**PROMPT 00:** BLOCKED — actual currently working off-device BOOT/DTB/DTBO
backups, active merged FDT and recovery manifest are absent from this ZIP.

**PROMPT 01:** Offline implementation + synthetic acceptance tests available;
formal real-device golden baseline exit gate BLOCKED by Prompt 00 evidence.

**CAMERA FLASH AUTHORIZED:** NO. **DEVICE WRITES:** ZERO.

Once Nuxel is reachable, resume Prompt 00 read-only and use this codebase to
validate the real golden baseline. Do not invent missing hashes or treat the
historical release image as a current backup.
