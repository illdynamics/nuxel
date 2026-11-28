# Nuxel S10+ S3NRN82 — NFC Endgame Prompt Pack

**Audit date:** 2026-11-22. **Evidence base:** `nuxel-ds-ssp (1)(1).zip` (repository snapshot), explicitly **not** a fresh live-device session. **Target:** Samsung SM-G975F `beyond2lte`, Exynos9820, downstream kernel 4.14.253, **A-only**, TWRP recovery available under the owner's agreement.

## Verdict and realistic plan

- **Estimated implementation maturity:** **45% (roughly 35–50%)** of the engineering work for **read-only NFC tag reading**. This is an estimate, not a measured percentage. **Verified physical tag acceptance: 0%** (zero accepted tag reads in supplied evidence).
- Most important historical wins: board identified, proprietary firmware hash verified, native daemon/parsers/UI built, **real controller bootloader conversation observed**. The most important unsolved physical gate: **verified controller NCI `CORE_RESET`/`CORE_INIT`, followed by RF discovery**.
- Several deterministic userspace bugs must be fixed **before** flashing: generic-netlink ACK handling, polling socket lifetime, missing AF_NFC sandbox access, invalid `NciController.set_target()` call; the grant gate can authorize a pending/ungranted record.
- **Known bootloop:** 2026-11-14 SHA1 CE fault in firmware download on BOOT kernel `#95`; whether a later safe implementation is running is **not verified**. A `0023` candidate patch exists but is optional in the wrapper and is NOT proof of device safety.
- Budget **3–6 serious Pro Thinking investigation/implementation rounds**, several inexpensive Flash verification rounds, and aim for **0–2 targeted BOOT flashes** if a kernel change is genuinely needed. Proprietary protocol/clock/firmware incompatibility could make it take longer; never promise a date or guaranteed success.

## Files and invocation

**Always attach `00_COMMON_MISSION_AND_NO_BRICK_CONTRACT.md` plus ONE step prompt to the agent.** Also give it the **actual latest on-device reports**, original ZIP/repo, and preceding round's report; do not rely on absent paths. Put the repo's existing `hw/NUXEL_01_NFC_S3NRN82_STANDALONE.md` on the agent's reading list.

1. `01_BASELINE_AND_LIVE_TRUTH_PRO_THINKING.md` — truth gate, no changes or flashes.
2. `02_USERSPACE_NETLINK_PERMISSION_FIXES_PRO_THINKING.md` — correct software bugs, write regression tests.
3. `03_KERNEL_FORENSICS_AND_SAFE_BUILD_PRO_THINKING.md` — SHA stack/auto-update/clock/driver arbitration audit. **No automatic flash.**
4. `04_NONFLASH_LIVE_NCI_DIAG_FLASH.md` — quick reversible validation, one failing layer at a time.
5. `05_HARDWARE_CLOCK_TRANSPORT_ESCALATION_PRO_THINKING.md` — only if physical NCI remains blocked; establish whether any DT change is justified.
6. `06_TWRP_CONTROLLED_FLASH_AND_ROLLBACK_PRO_THINKING.md` — **conditional** BOOT flash/recovery runbook, not automatically triggered.
7. `07_REAL_TAG_RF_ACCEPTANCE_FLASH.md` — real, owner-provided tags and permission tests; read-only.
8. `08_RELEASE_AND_LONG_TERM_REGRESSION_PRO_THINKING.md` — reconciliation, rollback tests, release docs and gate evidence.
9. `09_BLOCKED_PATH_AND_EVIDENCE_HANDOFF.md` — use if genuine proprietary/hardware blocker persists; protects boot and leaves precise handoff.

See `NFC_DEEP_AUDIT_2026-11-22.md` for detailed code findings, source paths, and the estimated maturity table.

## Decision rule after every round

- If **no normal Nuxel boot / recovery safety**: do **not** continue NFC experiments. Restore hash-verified golden BOOT, diagnose, ensure Nuxel returns.
- If **NCI is blocked before RF**: do **not** spend time on UI/tag scanning as a substitute.
- If **netlink fails with a permissions/ACK/socket-lifetime issue**: fix userspace before touching DT or flashing.
- If **controller only responds to bootloader commands**: diagnose proper transition/firmware state and hardware reference clock. No automatic firmware download.
- If **NCI and RF discovery work but no tag is readable**: debug activation/antenna/protocol and keep the flash boundary untouched.
- If **actual two tags succeed across cold reboot and sleep/wake**: finish integration and leave payment/eSE/HCE/tag writes explicitly out of scope.

**Owner agreement, accurately interpreted:** TWRP re-entry after an experimental reflash is a **failed Nuxel boot**, not a green light for the next blind flash. The agent must gather logs, restore the verified golden BOOT or make a demonstrably corrected candidate, and keep going only through unique, validated attempts. Never loop the identical failing image. If neither recovery nor the known-good BOOT can be verified, STOP writes and request physical intervention; no agent can promise zero-brick risk on an A-only device.
