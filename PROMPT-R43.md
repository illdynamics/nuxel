# NUXEL R43 — Custom authenticator
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r43-custom-authenticator`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Implement an offline TOTP/HOTP authenticator with secure seed import, encrypted-at-rest storage, time-drift awareness, lockout, backup/export, and masked UI. Seeds must never be logged, transmitted, or exposed to other apps.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `pwa/nuxel-apps/authenticator/app.json`, `pwa/nuxel-apps/authenticator/index.html`, `pwa/nuxel-apps/authenticator/tests/test-totp-vectors.js`, `pwa/nuxel-apps/authenticator/tests/test-vault.js`, `configs/nuxel/security/privacy-config.json`, and `configs/apparmor.d/usr.bin.nuxel-permissions`. The app declares `storage:encrypted`; the encryption/key-storage boundary must be verified, not inferred from the label.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns TOTP/HOTP generation, seed import/export, vault encryption/key handling, clock-drift checks, lockout, and UI masking. Does not own the system RTC (consume R13) or a cloud sync service. No seed logging and no network transmission of secrets.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Verify TOTP/HOTP against RFC test vectors and multiple time steps/digits/algorithms.
2. Define a secure vault format with authenticated encryption, per-install key derivation, and restrictive file permissions.
3. Implement QR/manual seed import with duplicate detection, validation, and no plaintext seed in logs.
4. Implement lockout/backoff, biometric/PIN/passphrase policy where available, and secure vault lock on background.
5. Add backup/export/import with explicit user consent and encrypted output; test wrong password/corrupt backup.
6. Handle clock drift/unsynchronized time and display a warning rather than generating silently wrong codes.
7. Audit screenshots, clipboard, logs, and app switching for seed/code leakage.

## Failure modes and diagnostics
- Watch for secrets in localStorage, console logs, QR screenshots, clipboard, and browser sync. A UI lock is not encryption. Verify key storage and file modes.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. RFC TOTP/HOTP vectors pass for all supported algorithms/digits/periods.
2. Vault data is authenticated-encrypted at rest and unreadable without the key.
3. Seeds never appear in logs, URLs, analytics, or screenshots; masking is tested.
4. Wrong password/corrupt backup/lockout fails closed without data loss.
5. Backgrounding locks the vault according to policy.
6. Clock drift produces a visible warning and the app does not claim codes are valid when time is suspect.
7. Export/import is explicit, encrypted, and reversible.

## Hardware, privilege and rollback safety
No network sync, no seed logging, no weak default PIN. Use synthetic test seeds only. Preserve user vault data on migration.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r43-custom-authenticator`, with tests and docs for this component only.
- `docs/component-reports/r43.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if secure key storage is unavailable; report BLOCKED rather than storing seeds in plaintext. Do not implement a cloud backup without explicit owner design.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
