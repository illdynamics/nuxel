# 04 — DEEPSEEK PRO THINKING: One Controlled, Owner-Approved CP Boot Trial

Read `00_MASTER_SAFETY_AND_TRUTH.md`, `09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md`, rounds 01–03 receipts. **No CP power/load action until explicit approval of the precise reviewed trial plan.** Approval of TWRP BOOT reflashing is not authorization to alter secure modem/NV data or run unreviewed CP commands.

## Preflight acceptance checklist (ALL must PASS)

- Device physically reachable with working Nuxel, Wi-Fi/SSH plus independent USB/TWRP recovery; exact current running BOOT/DT hashes and host known-good rollback image(s) verified. No DT/DTBO modifications whatsoever.
- Current CP state from real read-only ioctl captured immediately before trial. No active competing Android cbd/rild, no device node owner conflict, no kernel crash/pstore warning relevant to modem, correct ownership/permissions.
- Exact model build, decompressed CP primary image hashes and structural metadata; firmware not from another board; valid signed path as required; no plans to patch signature/TEE.
- Verified pinned S5000AP kernel UAPI and controller path, approved sequence/section mappings from matching `cbd`, fully logged dry-run compare and source provenance.
- No modem/CP/RADIO/EF(S|SG)/SEC_EFS/NV/calibration writes, no user-data overwrite, no generic fastboot; runtime takes firmware only from immutable verified private input.
- Process manager has `Restart=no` or tightly opt-in manual-only, `TimeoutStartSec` and per-stage bounded timeouts, exclusive ownership, clear abort paths; no infinite power/reset loops.
- Redacted state collection enabled: kernel journal, read-only `IOCTL_MODEM_STATUS`, service logs, IPC readiness markers. No raw SIM identities, RFS dumps or message payloads.

## Trial

1. Capture before snapshot: Nuxel health, current CP status, modem kernel log excerpt, `/dev/umts_*` permissions, relevant `/sys/class/net/rmnet*`, Nuxel default route. Preserve Wi-Fi, SSH and all user functions.
2. Under the approved execution manifest ONLY, invoke the pinned, reproducible `cbd`/loader once. Record each **actual** operation, return code, timestamp and target ABI state transition. Stop on first unexpected errno, invalid signature, timeout, crash state, abnormal power or thermal signal. Never blindly retry other offsets/binaries or alternate secure stages.
3. Observe `OFFLINE → BOOTING/LOADER_DONE → ONLINE` using verified real status and kernel source-defined state machine. Check CP reports stable online repeatedly, kernel logs provide boot confirmation, IPC channel can be safely probed without leaking personal data. No ONLINЕ claim from a tty, rmnet netdev or launched daemon alone.
4. If fails: quiesce service, preserve redacted evidence, verify Nuxel boot/USB/network still good, disable auto-start, mark `CP_BOOT_FAILED_<FIRST_STAGE>`. Return to offline source analysis; do not continually cycle the CP to 'make it stick'. If Nuxel itself fails and comes back in TWRP, execute the bounded BOOT-only rollback and offline root-cause agreement from `09`, not a blind repeat.
5. If stable ONLINE, document exactly which stage triggered readiness and potential RFS dependencies. A successful CP boot alone does not imply SIM, LTE, SMS or voice. Proceed to RFS/SIPC research.

## Deliverables

`reports/S5000AP-04-CP-BOOT-LIVE.md` with before/after hard evidence, exact signed candidate hash, binary SHA, key ABI UAPI hash, state/timing, unique trial ID, failure signature or success criterion, rollback status, no protected-partition-write attestation. Build reproducibility and source changes committed. If no explicit approval, STOP at a complete reviewable `CP-FIRST-BOOT-PROPOSAL.md` and continue only safe offline follow-up work.

### Flash subjobs allowed

Only retrospective source/trace analysis, documentation, and unit/integration tests using mock endpoints. No separate Flash agent owns live CP hardware.
