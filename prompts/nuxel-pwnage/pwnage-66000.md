# PWNAGE-66000 — KICKSTARTER

You are working in the Nuxel repository. Execute **`full-pwnage-66000.md`** as the authoritative implementation specification for making the Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820) Qualcomm QBT2000 ultrasonic fingerprint scanner work as a secure native Nuxel feature.

## Your instructions

1. Read `full-pwnage-66000.md` completely before editing anything. Inspect the whole repo, current git status, active S10+ build path and existing PWNAGE-45000/53000 evidence.
2. Continue from the existing working QBT2000 kernel driver and `/dev/qbt2000_fd` + `/dev/qbt2000_ipc` interfaces. Do not start over, mistake the sensor for Goodix, or assume generic `fprintd`/`libfprint` supports it.
3. Identify the exact pinned Linux4 Exynos 9820 kernel implementation, the actual S10+ TEE OS/client interface, and the matching vendor fingerprint HAL/trusted application. The captured `tzdev_iwi_event` is a clue, not proof that the fingerprint TA is available. Do not transplant QBT1000/QSEE code into this Exynos QBT2000 stack without exact ABI evidence.
4. Implement every safe part: provider diagnostics/state machine, TEE/vendor integration where genuinely possible, secure enrollment/authentication, one-time challenge verification, Settings and lock-screen UX, root Bridge integration, device permissions, power lifecycle, PIN fallback and tests.
5. **Never** expose raw fingerprint data/templates, treat a finger-detect IRQ as a match, accept a UI boolean as proof, bypass TrustZone/TEE/secure boot, or weaken the lock/PIN fallback. Audit the existing fingerprint-mode fallback verifier path; the stored fallback verifier may not currently be checked by the generic PIN verifier.
6. If the exact signed TA/vendor stack or compatible secure assertion path is missing, finish all non-blocked work and report the precise dependency. Keep biometric unlock disabled; do not fabricate success.
7. Build/test with repo-native commands. Do not flash unattended. Deliver the implementation, tests, `PWNAGE-66000-REPORT.md`, TODO ledger, security design note, deployable userspace ZIP, Wi-Fi SSH deploy instructions and rollback.

Work autonomously and in the required phase order. The goal is a real physical fingerprint enrollment and secure lock-screen unlock on the S10+, with the PIN fallback always working. Do not return a research-only report when implementation is possible.
