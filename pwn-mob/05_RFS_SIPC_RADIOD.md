# 05 — DEEPSEEK PRO THINKING: Verified S5000AP RFS + SIPC5 Control + Native Radio Daemon

Read `00_MASTER_SAFETY_AND_TRUTH.md`. Requires **real CP ONLINE gate** from round 04 for physical protocol tests; do all static/host work otherwise. Keep boot/DT frozen. Do not fake protocol success.

## Determine the correct reusable stack

Research same-generation Samsung S10 vendor `rild`, `cass`, `libsec-ril`, RFS/IPC integration as available from owner-licensed vendor runtime and pinned Exynos9820 Lineage device tree; compare lawful reusable source against the exact `sipc5.h` and I/O-channel mapping in the running `modem_v1`. Evaluate architecture (1) narrow matching Samsung vendor RIL in isolated Bionic runtime with D-Bus bridge, (2) reconstructed minimal native SIPC5 `nuxel-radiod`, (3) proven FOSS alternative. **Do not assume ModemManager speaks SIPC by itself.** Choose on demonstrated protocol coverage, licensing, safety, maintenance and binary ABI.

## SIPC receive/parse/test first

Map `/dev/umts_ipc0`, `umts_ipc1`, `umts_rfs0`, `umts_cass` and any actual target endpoints from kernel source and live `udev`, not from Android generations with different channels. Design a single authorized device owner with read worker and nonblocking bounded queue; parse start/header, length, channel ID, message class/sequence/correlation, endian, fragmentation, unsolicited notifications, timeout, reconnect and unexpected CP reset. Compare each byte meaning against pinned source or redacted authorized trace before issuing commands. IPC endpoints may contain subscriber information: do not blindly `cat`, dump or commit captures.

Host tests for truncated frames, length overflow, malformed flags, replayed sequence, unexpected response, dropped fragmented frame, racing requests, CP restart, zero read and unavailable endpoints. Fuzz the parser under memory/time caps; test all writes disabled in offline simulation. Never treat an echo fixture as a real RIL response.

## RFS (highest privacy/safety risk)

Research exact Samsung S5000AP RFS protocol. Establish required operations and access paths from permitted source/owner-approved redacted trace. Implement strict allowlist for only proven necessary non-secret files, reject `..`, absolute unexpected paths, symlinks/hardlinks, escapes, direct block devices, EFS/EFSG/SEC_EFS, NV, calibration/keys, writable carrier identifiers. No filesystem service exposing arbitrary phone host paths to CP; if legitimate CP boot absolutely requires protected NV access, stop and clearly report rather than bypass.

## Native service capabilities

Produce `nuxel-radiod`/bridged RIL with versioned D-Bus API and caller authorization for: CP state, radio state, SIM readiness and PIN-required flag, available RAT/operator/registration, signal metrics, bearer create/delete, counted bytes and real feature flags. Avoid APN/PIN/SMS leakage; only actual modem sources can populate fields. Redact identifiers centrally. A daemon ONLINE means daemon alive, **not** modem/cellular available.

## Physical acceptance

Require documented genuine CP IPC requests and distinct valid responses at permitted low-risk read-only stage. Real RFS if needed is independently verified. Observe CP for stable idle and crash recovery. No fabricated registration/data fields. Produce `reports/S5000AP-05-RFS-SIPC.md` including protocol coverage table (`KNOWN`, `IMPLEMENTED_TESTED_HOST`, `LIVE_VERIFIED`, `UNKNOWN`), source lineage/license, unit and fuzzer receipts, security review, crash behavior, no-SIM negative test if permissible. Commit focused, robust source and systemd/udev tests.

### Flash subjobs

A. RFS security parser + tests. B. SIPC5 packet parser + fuzz tests. C. Vendor runtime feasibility/ABI decision matrix. D. D-Bus API contract and permissions. Thinking owns integration and any authorized live test.
