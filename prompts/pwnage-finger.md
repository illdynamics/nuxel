# PWNAGE FINGER — S10+ QBT2000 + TEEGris Fingerprint for Nuxel

**Read and follow `full-pwnage-finger.md` completely.** It is the binding engineering, security, permission-manager, test and reflash specification.

## Mission

Bring up real Samsung Galaxy S10+ (`SM-G975F`, `beyond2lte`, Exynos 9820) QBT2000 ultrasonic fingerprint enrollment/authentication on Nuxel. Integrate it into the lockscreen and Nuxel permission manager, deploy safe userspace changes live over SSH, and prepare any secure-world/vendor/kernel additions for the single combined reflash batch.

This is not a fake API/UI task. The actual secure provider must work.

## What the repository already proves

- `/dev/qbt2000_fd` and `/dev/qbt2000_ipc` exist in captured device evidence.
- `/sys/class/fingerprint/fingerprint` reports `QBT2000`, vendor label `QCOM`, `type_check=7`.
- The Samsung QBT2000 kernel driver is present and probes.
- The current bridge provider is deliberately `BLOCKED_SECURE_PROVIDER`; enrollment/delete/test correctly refuse.
- No verified QBT2000 TA, vendor fingerprint HAL or trusted provider is included in the uploaded repository.
- Device nodes were root:root `0600`; preserve that. Never expose them to normal applications or the `audio` group.
- The target is Exynos 9820 and uses TEEGris 3.1—not the Qualcomm S10+'s QSEE 5.2 stack.
- One captured boot has a `startup.tzar` unpack failure because `bin/libtzld.so` has an incorrect hash; a separate log segment shows a later loader completion. Reconcile the actual current boot rather than assuming TEE is entirely missing or entirely working.

## Immediate critical tasks

1. Inspect current `git status`, `REFLASH-PLAN.md`, `REPORT-FINGERPRINT.md`, kernel source, fingerprint provider, security provider, permission manager and current deployed files. Preserve the concurrent NFC/USBNET changes; no reset/stash/clean/revert.
2. Run the included read-only acquisition helper when the exact S10+ is attached:

   `bash scripts/acquire-s10plus-fingerprint-evidence.sh`

   It writes only to the workstation. It must not read/write `persist`, EFS, RPMB, user biometric storage, secure memory or raw QBT node data.
3. Identify the exact QBT2000 vendor HAL/client, TEEGris TA, ABI, build ID, signed container, secure IPC and secure storage protocol. Verify provenance and signature. If absent, determine if it can lawfully be obtained from an exact matching Samsung firmware/OEM-authorized source.
4. Fix any proven TEE startup/container integrity mismatch using a coherent authorized vendor set. Never patch hash/signature verification off, self-sign a TA, or mix QSEE/Qualcomm artifacts.
5. Implement a genuine secure provider adapter. No libfprint userspace matcher, no raw image/template exposure, no fake `matched=true`, no bypass of anti-spoof or lockout.
6. Fix the fingerprint-mode PIN fallback bug: current code stores `fallback_pin_salt`/`fallback_pin_verifier`, but the unlock path checks only `salt`/`verifier`. Add mode-aware verification and persistent lockout tests before enabling fingerprint.
7. Fix Bridge API authorization: `fingerprint`/`biometrics` mutations (enroll/delete/test/manage) are currently not included in the owner-only mutation guard. Restrict management to verified Settings owner identity, and derive caller identity from the authenticated bridge context—not JS parameters.
8. Add proper canonical permission-manager capability mapping: app-scoped `biometric:authenticate` and separate system-only `biometric:manage`/enroll/delete. Default deny; no broad app grants. Update canonical `capabilities.json`, permD alias resolution, Permission Manager `CAP_LABELS`/`CANONICAL`/`TOKEN_MAP`, API gates, config grants and tests together. A third-party app gets a challenge-scoped OS prompt result only; it cannot unlock the device or manage enrollment.
9. Keep QBT device nodes root-only. Do not claim systemd DeviceAllow or AppArmor is enforcing unless the actual 4.14 image proves it.
10. Extend existing Settings Fingerprint UI and Quick Settings status truthfully. No ON/READY state until the TEE/TA provider reads back healthy.

## Secure authentication requirements

All acquisition, enrollment, matching, template storage and anti-spoof must remain inside the verified TEE/provider. The OS must use a fresh random challenge, validate the genuine vendor-signed/HAT-equivalent proof, bind it to the active user/session/operation, reject replay/stale/wrong-caller results and consume it once. The browser never decides authentication. Any TEE/provider failure leaves the lockscreen locked and PIN fallback available.

## Live deployment and one-flash policy

Deploy safe userspace components (provider status, security fallback fix, API permissions, canonical permission registry/UI and Settings PWA) over the existing SSH path only after regression tests, backups, identity checks and hashes. Confirm the live Permission Manager shows the biometric capability and that grants/denies are enforced/audited. If no authorized TA exists, keep UI/provider clearly BLOCKED; do not claim fingerprint is live-working.

Do **not** flash/reboot/switch slots in this task. Any secure-world/vendor/TA payload and proven kernel/DT patch must be prepared for the one coordinated A/B batch with NFC, USBNET and other hardware work. Preserve the current known-good slot and PIN access.

## Required physical tests

After the authorized combined image is deployed: enroll a real finger via the trusted UI; authenticate repeatedly through the real lockscreen challenge; reject a non-enrolled finger; test timeout/cancel, lockout and provider failure; verify PIN fallback; delete the enrollment and prove it no longer authenticates; reboot and verify secure persistence. Perform official anti-spoof tests only if vendor tooling supports them. Synthetic tests never count as physical PASS.

## Deliverables

Create:

- `PWNAGE-FINGERPRINT-REPORT.md`
- `PWNAGE-FINGERPRINT-TEE-ANALYSIS.md`
- `PWNAGE-FINGERPRINT-PERMISSION-MATRIX.md`
- `PWNAGE-FINGERPRINT-TEST-RESULTS.md`
- `PWNAGE-FINGERPRINT-REFLASH-MANIFEST.md`
- source changes, registry/UI mappings, regression tests, service policy, hashes and acquisition evidence.

Report exactly what is PASS, PARTIAL, BLOCKED_VENDOR_TA, BLOCKED_TEE_INTEGRITY, BLOCKED_COMPATIBILITY, FAIL or NOT TESTED.

**Do not stop after a clean compile or UI update. Keep investigating and implementing until real secure enrollment/authentication works—or until a genuine OEM signing/TA/compatibility dependency is conclusively proven unavailable. Never bypass the TEE to force a false success.**
