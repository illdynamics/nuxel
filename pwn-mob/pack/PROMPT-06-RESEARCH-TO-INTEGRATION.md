# DEEPSEEK PRO THINKING — STAGE 06, SOURCE-GROUNDED TELEPHONY PROTOCOL RECOVERY

You are continuing Nuxel's native S5000AP cellular integration, NOT starting a new bring-up. This prompt is intended for a shell-connected agent with the **actual current Nuxel repo**. This ZIP is a research/evidence aid, not a tested Nuxel source patch.

## Context — user-reported, verify live

- Device Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, kernel 4.14.253, no Android userspace dependency desired.
- Existing `cs/mob`, reported HEAD `c050c75c` after Stage 05.
- Stage 04 physical CP ONLINE demonstrated; Stage 05 `nuxel-radiod` built and running with real CP→AP FMT/RFS reception.
- Reported live FMT `AST_POWERON` (`main=0x13`, `sub=0x05`, `type=0x03`), and 25-byte RFS message containing `DELETE_ALL_VIS`.
- Native D-Bus `nl.nuxel.Radio1`; no verified SIM telephony commands, LTE registration or bearer creation.
- CP firmware was reported as EFUJ2; full current installed RADIO SHA256 `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` (must re-verify if consequential).
- The user's Stage 05 report says BOOT/DT baseline unchanged and CP ONLINE. Do not presume those conditions still hold without read-only checking.

## Research findings already verified externally

Read `FINDINGS.md`, `SOURCES.md` and the cited online repositories. Highest-value discoveries:

1. LineageOS Exynos9820 common config explicitly sets `cbd` to `sipc` and legacy SIPC ioctls.
2. Its proprietary-file manifest names vendor RIL, SIM, radio and bridge shared libraries. Common manifest defaults to N975F source; that **is not** an exact match for G975F EFUJ2.
3. LineageOS beyond2lte manifest tracks SM-G975F stock firmware provenance separately.
4. BaseMirror (`https://github.com/OSUSecLab/BaseMirror`) is public **offline** static command-extraction software. Its paper includes SM-G973F S10 and Ipc41X; this is sibling evidence, not a verified S5000AP/EFUJ2 mapping.
5. Legacy `libsamsung-ipc` is reference material, NOT a matching protocol implementation.

## Objective

Recover a verifiable, version-specific **semantic map** of the minimum SIM, network-registration and mobile-data messages, then safely implement source-backed native Nuxel handlers. Keep the existing kernel, CP bootstrap and radio transport unless a specific reproducible defect disproves the current design. Stage 06 cannot be declared complete solely from research, parser tests or newly compiled components.

## Workflow

### A. Preserve device and verify repository

- `git status`, `HEAD`, relevant commits and reports; ensure no worktree loss.
- Read-only `modem_state`, CP uptime/boot history, current daemon status; never reboot to create test traffic.
- Confirm `radiod` exact read semantics in pinned kernel code before modifying frame parsing.
- Preserve verified Stage 04/05 hashes and owner authorization gates. Do not redo bootstrap automatically.

### B. Search for *local authorized* Samsung vendor RIL references

- Check owner's existing stock AP/vendor backups, firmware extraction directories, previously retained disassemblies, local artifact indexes and Nuxel history. Search for both 32-bit and 64-bit `libsec-ril.so`, `libsec-ril-dsds.so`, `libril_sem.so`, `libsecril-client.so`, `rild`, `cbd`, radio-specific `.so` and RFS handlers.
- Prefer **the exact SM-G975F stock AP/vendor build paired with the installed CP firmware**. Document fingerprint/build, SHA256, architecture, source and permission to analyze. Note when exact EFUJ2 matching remains unavailable.
- Do NOT install or run Android vendor ELF libraries inside Nuxel. Do NOT copy proprietary binaries into public repo, reports, prompts or ZIPs.
- Run `scripts/inventory_vendor.py`, `scripts/triage_elf.py` on local host copies. Review their output before sharing.

### C. Recover protocol semantics without making up command IDs

- Use static RIL analysis (Ghidra and optionally the BaseMirror **RIL_Analyzer** offline components) if owner-authorized files exist. Never invoke BaseMirror `automatic-testing` or attack-payload subprojects against the phone.
- Locate actual message packers and IPC send/receive sinks, their header fields, relevant constructors, SIM state, operator/network state, bearer setup/teardown code paths.
- For each possible command log the exact source binary hash, source file/function/offset, component, payload layout and reason its semantics follow; mark unknowns explicitly.
- Cross-check with Nuxel's pinned `modem_v1` framing and with approved read-only captures. Use semantic grades in `REFERENCE-RECOVERY-WORKFLOW.md`.
- Produce a versioned `data/telephony-command-matrix.csv` with **no invented entries**.

### D. Keep RFS as a separate protected security gate

- Compare real RFS framing and the legacy conceptual model, but never translate old Samsung opcodes directly to S5000AP.
- `DELETE_ALL_VIS` is text from a real record, **not** an authorized filesystem operation or proven reply contract. Keep it deny/fail-closed.
- Review actual read/write operation requirements independently. If modem needs NV/EFS, preserve the owner gate: no access or emulated success without review.
- Do not treat 2040-byte read chunks as application messages until the kernel skb/ring buffer path explains them.

### E. Implement incrementally

- Restrict initial live goals to **documented read-only SIM status**, then validated registration observation. Add bearer only after verified protocol requirements, carrier/APN configuration and a separate review.
- No unknown command transmissions. No speculative APDU, RFS writes, modem resets, crash ioctl, or carrier/network attach attempts.
- Add bounded parser/packer unit tests, malformed frame tests, source-backed state-machine transitions, rollback for reversible userspace changes, and privacy redaction.
- Continue all safe offline coding/tests/build/debugging autonomously. For a gated physical modem or protected storage operation, state exact necessity and obtain fresh owner approval before acting; never brute-force by repeated requests.

### F. Report faithfully

Create/update `reports/S5000AP-06-TELEPHONY-PROTOCOL.md` with:

1. Current source HEAD and kernel/CP state.
2. Found exact-matching vendor references (or a clear missing-reference statement).
3. Vendor build provenance and ELF fingerprints (no binaries in report).
4. Source-backed request/response map with O1–O6 evidence grades.
5. Known RFS dependencies and still-blocked operations.
6. Actual modem SIM state (distinguish `ds_detect=1`).
7. Network registration, data-bearer outcomes (positive only if verified live).
8. Test receipts, resource lifecycle, security assessment and unchanged protected partitions.
9. Remaining blockers and the smallest necessary owner action.

Final verdict must be one of:

- `STAGE_06_RESEARCH_COMPLETE_IMPLEMENTATION_PENDING`
- `STAGE_06_SAFE_LIVE_SIM_VERIFIED`
- `STAGE_06_REGISTRATION_VERIFIED_DATA_PENDING`
- `STAGE_06_LTE_DATA_VERIFIED`
- `STAGE_06_BLOCKED_NEEDS_VERSION_MATCHED_REFERENCE`

Use the strongest **supported** verdict, not an optimistic future objective.

## Non-negotiable

No fabricated Samsung telephony vocabulary; no unauthorized modem interaction; no change to BOOT/DTB/DTBO/RADIO or protected NV/EFS; no false declaration that ModemManager detection is required for native `radiod` to receive messages. Preserve working Nuxel and existing recovery access.

START by reading the attached research files and auditing the current repo, then complete every safe offline phase. If closed-source semantics remain truly unavailable, deliver exact, reproducible evidence and a tightly scoped next step rather than guesswork.
