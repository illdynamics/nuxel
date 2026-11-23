# 08 — DEEPSEEK PRO THINKING: Full Regression, Release/Handoff and Truthful Percentage Update

Read `00_MASTER_SAFETY_AND_TRUTH.md` and all reports 01–07. Complete engineering work, not another speculative summary.

## Repeatability audit

Record complete baseline and final `git diff`, branch, commits, firmware provenance/hash (no binary redistribution), source upstream SHAs, built ARM64 ELF/interpreter/deps, kernel/BOOT/embedded-DTB hash and DTBO unchanged attestation. Check init order (CP boot service then RFS/radiod then ModemManager/NetworkManager), failure behavior and no boot blocking on offline CP, proper low-privilege services and no endless restarts. Test cold boot twice, Nuxel health, on-demand radio start/stop, CP restart behavior, suspend/resume, airplane mode, SIM absent/PIN-required/registered/rejected, bearer start/stop, DNS/IPv4/v6, modem crash and service restart, prolonged idle, battery/thermal budget. Preserve Wi-Fi/SSH USB GNSS NFC camera audio sensors touch display power button, screen rotation and local user data.

## Source and CI

Run full host suites: `modem-diag` honest state, kernel ABI/layout assertions, firmware container rejection, cbd offline integration, SIPC fuzz and malformed framing, RFS path traversal/permissions tests, ModemManager port probe/udev plugin, network profile/route and failover tests, SMS/call/IMS capability flags, app UI offline and no-SIM. Host `PASS` **does not establish** a physical layer. All tests produce machine-readable receipts with authoritative source. Never edit baseline historical evidence.

## Documentation refresh and exact completion

Produce final `reports/S5000AP-RADIO-FINAL-RECOVERY.md` + a concise user summary and matrix:
- AP kernel driver/probe
- CP archive identity/signature/compatibility
- Samsung CBD ABI and actual boot
- RFS and SIPC response
- SIM detected/ready
- carrier registration
- mobile data PDP, `rmnet` IPv4/v6, DNS, cellular HTTPS with Wi-Fi out of path
- reconnection/airplane/reboot
- SMS send/receive
- ordinary calling and two-way audio
- IMS/VoLTE
- app UI/permissions and regression

For each: `VERIFIED_LIVE`, `HOST_TESTED`, `SOURCE_ONLY`, `BLOCKED`, `FAILED`, with timestamp/evidence and a conservative weighted completion estimate. A data-only project can be 100% data while 0% voice or IMS; never report a single unsupported all-features 100%. Include exact minimal remaining prerequisites and realistically staged next prompts if any remain.

## Flash/recovery after a regression

If a BOOT flash is necessary, run the exact bounded documented `09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md`. TWRP re-entry after flashing = **candidate failed**. Investigation and rollback first; new distinct image only with verified compile/preflight/approval. Never write DTBO or protected modem partitions. A successful Nuxel return is validated by running system/kernel hashes and UI/network services, not by absence of TWRP.

## Delivery and release

Deliver source changes, test results, unit files, install/rollback manifests, and verify clean repository. Make scoped commits; PR/release only under owner's existing workflow if authorized. If a stage is impossible without proprietary artifacts, carrier provisioning or owner consent, mark BLOCKED with exact needed input, not “complete”. Do not mask remaining failures with a green dashboard.
