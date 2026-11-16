# FULL-PWNAGE-73000 — Finish and prove PWNAGE-63000 on the live S10+ (Vault, keyring and Authenticator)

**Mission type:** finish-off / live acceptance / physical verification for `full-pwnage-63000.md`.
**Relationship to 63000:** the 63000 source, packaging, tests and userspace deployment already exist. The current live check shows the installed 63000 files match the canonical source and the Secret Service provider is running. The missing work is not a blind redeploy: it is owner-assisted keyring initialization, live Vault/Authenticator acceptance, suspend/re-lock behavior, migration/recovery checks, and any source/deploy drift found during re-verification.
**Repository:** `/x/nuxel` (Git root), branch `main`, baseline HEAD `0bed35d881ba674a21f67d31501e84f1031992b5`. Re-verify; do not assume.
**Prompt suite:** `/home/wicked/Desktop/nuxel-pwnage/`.
**Target:** `root@10.20.30.16`, key `$HOME/.ssh/wicked_wqn_id_rsa`, strict host-key checking, bounded SSH timeouts.
**Owner request:** finish the remaining PWNAGE-63000 task on the phone. This authorises userspace deployment if source/live drift is found, service restarts, and normal owner-approved reboots over Wi-Fi SSH. It does **not** authorise TWRP, kernel/DTB/BOOT/firmware/partition writes, bootloader changes, keyring deletion/re-keying, credential export, or inspection of secret values.

---

## 0. Current verified state (2026-11-03 ~23:46 CET) — re-verify, do not assume

### 0.1 Source state

- Git root `/x/nuxel`, branch `main`, HEAD `0bed35d881ba674a21f67d31501e84f1031992b5`.
- 154 dirty owner paths are present. Preserve every one; do not reset, clean, stash, commit or push.
- The 63000 worker made no tracked source changes; it verified the existing implementation and left a report at `/x/nuxel-pwnage-runs/20261103-160408/missions/63000/worker-final-report.md`.
- Host verification already passed:
  - Secret Service Vault implementation and capability scoping;
  - encrypted export/import, CSPRNG, auto-lock;
  - TOTP/OATH vectors;
  - registry, Nuxtore bundle and package integrity;
  - deploy artifact SHA-256 `899fffca24c46ca468ab84976340b1725efdc9735084f198b904fcd248008818`.
- Known stale test drift: `tests/pwnage49000/test_pwnage49000.py::test_cache_version_bumped` still asserts `v62000-pw62000` while the tree intentionally carries a newer cache version. This is a pre-existing test defect, not a 63000 secret/security failure. Fix it only with a dated, clearly attributed change.
- The host may lack the `pytest-check` plugin for `tools/s10plus/a33/tests/test-packages-manifest.py`. Record that as an environment limitation or use a bounded isolated environment; do not claim the suite passed if it did not run.

### 0.2 Live phone state (strict Wi-Fi SSH, read-only probe)

- Target identifies as `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820`; `uname -m` is `aarch64`; kernel `4.14.253-gf7194c1d15ed-dirty`; boot ID `e3b5e426-5c2b-4ac8-ad14-70e2cfb27ab4`.
- `nuxel-wayland`, `nuxel-http-bridge`, `nuxel-bridge` and `nuxel-web` are active.
- `org.freedesktop.secrets` is owned once on `unix:path=/run/nuxel-wayland/bus`; observed `PID=115898`, `UID=0`, `EUID=0`.
- Packages: `gnome-keyring-48.0-3.fc43.aarch64`, `gcr3-3.41.1-11.fc43.aarch64`, `libsecret-0.21.8.2-2.fc43.aarch64`.
- Durable deployment receipt `/var/lib/nuxel/p63000-deploy.json` reports `status=deployed_userspace_and_rebooted`, post-reboot verified `2026-11-03T11:37:06Z`, backup `/var/backups/nuxel/p63000-20261103T113054Z`, pre-mission rollback backup `/var/backups/nuxel/p63000-20261103T111313Z`.
- `/run/nuxel/p63000-deploy.json` and `/run/nuxel-p63000-backup-dir` are absent because `/run` was cleared by a later boot. The durable receipt is authoritative for the prior deployment.
- Live 63000 file hashes match the canonical source:
  - `/usr/lib/nuxel/nuxel-bridge/api.py` `aab569150a9f489b60acfe96c0188702f688e231158dd73ffb8bd7e0ca569479`;
  - `capabilities.py` `09491c673eae7c34d015cb8918d872116da6edff8a6a090f216e9b275b2573d9`;
  - `secret_service.py` `11dfb11a145819a5879749c087465880814130ee047dfec6f17e6b02486c6a56`;
  - `keyring_api.py` `d3d8aa15f3fa5a34c80b02404ad46ad489dfc16fcea4fa05e84e51ff875fd9f4`;
  - `/etc/systemd/system/nuxel-http-bridge.service` `45a593dd8a2dadbc3330f1025dcb78b541ed2d50042958be03fe342d914e59f5`;
  - `/usr/share/nuxel/pwa/nuxel-common/bridge.js` `ced52672bccd82aaa916360bc13146f0b69b2c5540ddc0337ea6d129132f0048`;
  - `/usr/share/nuxel/pwa/nuxel-common/app-registry.json` `610097c560f40109e13aa105e6cc33a49eeecf974e96c03aefe1b5945da6e739`;
  - `/usr/share/nuxel/pwa/nuxel-apps/vault/index.html` `7cfcfecba2bed4f1aa63c6fd483dca500f11842bfc57a77b3ce0049f58c41294`;
  - `/usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html` `822bdf1c3243c5dc37e354a7ea53d94ec4c65f870649b376082dade301176ad5`;
  - `/usr/lib/systemd/system-sleep/nuxel-keyring-lock` `de0cfe24f73b9e7b1db2d1d0b13dc25cc8a21e78c1e3bde0858be4b0fafd3100`.
- `/etc/nuxel/keyring-launcher.secret` exists, mode `0600 root:root`, size 65 bytes. Do not read or print its contents.
- `/root/.local/share/keyrings/login.keyring` is **absent**; the owner has not initialized the keyring/vault on this boot. The deployment receipt also records `keyring_initialized_by_agent=false` and `keyring_files=0`.
- The historical receipt records an Authenticator envelope of 654 ciphertext-only bytes; do not inspect or export it.

### 0.3 What is actually missing

1. **Owner initialization.** Vault cannot become `unlocked` until the owner creates the master password. The agent must never choose, see, type, log or store that password.
2. **Live acceptance.** Vault create/lock/unlock/delete/copy, Authenticator link/auto-unlock, TOTP enrollment, export/import, wrong-password fail-closed, suspend/resume re-lock and permission isolation have not been fully re-proven on this boot.
3. **Migration/recovery.** Confirm that an Authenticator reset does not delete Vault items, that encrypted export/import works, and that rollback preserves the keyring and envelope.
4. **Source/deploy drift check.** The current live hashes match, but re-verify after 72000. If anything drifts, update the deploy set and install atomically with a verified backup. Do not blindly run the old archive if it would overwrite newer 62000 fixes.
5. **Documentation/test cleanup.** The stale P49000 assertion and any deploy-artifact mismatch should be fixed or precisely classified.

### 0.4 TWRP / reflash answer

**No TWRP and no reflash are needed for PWNAGE-63000.** This mission installs and tests userspace files, a PWA, a bridge service, a Secret Service backend and a suspend hook. The kernel, BOOT, DTB, modem, EFS and partition table are untouched. Everything can be done over the existing Wi-Fi SSH root shell, with a normal reboot only if the session script or native host needs reloading. TWRP would only be relevant to a separate kernel/partition recovery scenario, not to this task.

---

## 1. Objective and definition of done

Close PWNAGE-63000 on the actual S10+:

1. Re-verify source/live parity and the Secret Service provider.
2. Deploy only if real drift exists, with an atomic backup and rollback.
3. Have the owner initialize the Vault with their own master password.
4. Prove the Vault lifecycle with disposable data and no secret leakage.
5. Prove Authenticator linking, auto-unlock gating, TOTP handling and reset isolation.
6. Prove suspend/screen-lock re-lock and service-restart behavior.
7. Prove capability isolation: a Home token cannot act as Vault; an unauthorized app is denied.
8. Prove encrypted export/import and rollback preservation without exposing secrets.
9. Re-run all host suites and produce a dated evidence bundle.

`PHYSICALLY_VERIFIED` requires an actual owner-assisted test on the S10+ with observed behavior. A matching hash, an active service, a bus owner or a mocked unit test is not enough.

---

## 2. Non-negotiable security and safety rules

- **Never** read, print, export, decrypt, hash-as-proof or persist any vault item, password, master password, recovery code, TOTP/OATH seed, Authenticator envelope, keyring file, private key or credential-store content.
- Do not run commands that dump `secret-tool` values, keyring files, browser `localStorage`, the Authenticator envelope, or bridge logs containing values.
- Do not create, reset, re-key, migrate destructively, unlock/lock, or erase the owner's keyring or credential state. The owner initializes and unlocks it.
- Use disposable test data only. A test TOTP secret may be generated in a private temp file or passed via a non-echoing helper, but its value must never appear in logs, screenshots, reports, shell history or evidence.
- Do not modify file ownership/permissions of live credential stores. You may inspect file metadata (mode, owner, size), not content.
- Do not start/stop/restart the bridge or keyring in a way that risks losing an active owner session without recording the state and obtaining approval. Normal service restarts performed by the canonical deploy script are allowed when a deployment is actually needed.
- Do not use TWRP, flash, repartition, change USB role, factory reset, or write to EMMC/EFS/modem partitions.
- Preserve `PIN/password` fallback and the existing screen lock. Do not bypass the lock screen to test the vault.
- Do not claim Microsoft Authenticator push, number matching, passwordless or PRT support. This is an OATH/TOTP implementation unless independently proven otherwise.
- Preserve all existing TOTP accounts and the existing Authenticator envelope across deploy/rollback.

---

## 3. Execution order

### Step 0 — baseline and preflight (read-only)

1. Verify Git root, branch, HEAD and the 154 pre-existing dirty paths. Checkpoint the diff.
2. Verify the SSH key exists/readable; never print it.
3. Record target model, `uname -m`, kernel, boot ID, uptime and active services.
4. Record package versions for `gnome-keyring`, `gcr3`, `libsecret`.
5. Record `busctl --address=unix:path=/run/nuxel-wayland/bus status org.freedesktop.secrets` owner PID/UID/EUID only.
6. Record metadata only for `/etc/nuxel/keyring-launcher.secret` and keyring files: path, mode, owner, size. Do not read contents.
7. Record whether `login.keyring` exists and whether the Vault status API reports `not_initialized`, `collection_locked` or `unlocked`.
8. Record the durable deployment receipt, backup paths and artifact SHA-256.

### Step 1 — source/live parity and host gates

1. Compare every canonical 63000 source file to its live target with SHA-256.
2. Re-run the 63000 host suites:
   ```sh
   python3 -m pytest -q tests/pwnage63000/test_secret_service.py
   python3 -m pytest -q tests/pwnage63000/test_vault_app.py
   node --test tests/pwnage63000/test_bridge_keyring.mjs
   node pwa/nuxel-apps/authenticator/tests/test-vault.js
   node pwa/nuxel-apps/authenticator/tests/test-totp-vectors.js
   node pwa/nuxel-apps/vault/tests/test-archive.js
   node pwa/nuxel-apps/vault/tests/test-pwgen.js
   python3 tools/s10plus/a33/verify-app-registry.py
   python3 pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py
   ```
   Use the repository's current canonical paths if a path differs; record the exact path used.
3. Fix the stale `test_cache_version_bumped` assertion to the current Home cache version if it is still failing for that reason, or record it as a precise pre-existing defect. Do not touch the cache version itself merely to satisfy an old test.
4. If `pytest-check` is unavailable, report the collection limitation and optionally run the package-manifest test in a bounded isolated environment. Do not silently skip it.
5. Verify `release/pwnage63000/nuxel-pwnage63000.tar.gz` against its `.sha256`. If 72000 changed shared files, rebuild the 63000 artifact from the current tree so it does not carry stale 62000 files.

### Step 2 — deploy only if drift is real

If source/live hashes match and the deployment receipt is valid, do **not** redeploy merely to create activity. Record `INSTALLED` and proceed to acceptance.

If drift exists:

1. Create a verified backup under `/var/backups/nuxel/p63000-<UTC>/`.
2. Verify the backup `SHA256SUMS`.
3. Confirm the deploy script will preserve:
   - the current keyring and keyring files;
   - the Authenticator envelope;
   - `/etc/nuxel/keyring-launcher.secret`;
   - current Home manifest/registry fixes from PWNAGE-72000 and 63000;
   - the current native host.
4. Run:
   ```sh
   SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
     tools/pwnage63000/deploy-pwnage63000.sh root@10.20.30.16
   ```
5. Verify the service restarts, the scoped API status and the identity-mismatch test.
6. A normal owner-approved reboot or `systemctl restart nuxel-wayland` may be used only if the native host/session script changed. Prefer the least disruptive reload.
7. If deployment fails, roll back with the new backup. Never delete keyring data to recover.

### Step 3 — owner-assisted Vault initialization

The owner must perform the following; the agent must not watch, capture or record the password:

1. Unlock Home.
2. Open **Vault**.
3. Create the keyring/master password.
4. Confirm the UI reports the vault as initialized/unlocked.
5. Do not enter a real production secret until the basic disposable lifecycle test passes.

After the owner initializes it, the agent may run **read-only status**:

```sh
busctl --address=unix:path=/run/nuxel-wayland/bus status org.freedesktop.secrets
```

and the scoped Vault status API. Never print item content.

### Step 4 — Vault lifecycle with disposable data

Using only disposable test entries:

1. Create an item; confirm it appears.
2. Edit it; confirm the change is stored.
3. Copy it to the clipboard through the UI; confirm the expected value, then clear the clipboard.
4. Lock the collection; confirm the UI and API report `collection_locked`.
5. Attempt to read the item while locked; it must fail closed.
6. Unlock with the owner-entered password; confirm the disposable item persists.
7. Delete the disposable item; confirm it is gone.
8. Lock again; confirm no secret is retrievable from the DOM, bridge API or logs.
9. Search the bridge log and test transcript for the disposable sentinel value; it must be absent. Use a unique non-sensitive sentinel, not a real secret.
10. Verify the launcher secret is still `0600 root:root` and the native host contains `NUXEL_KEYRING_MINT`.

### Step 5 — Authenticator integration and TOTP

1. Open Authenticator; confirm it fails closed while the keyring is locked.
2. Link/unlock through the existing consent flow; do not bypass consent.
3. Confirm auto-unlock only works while the keyring is unlocked.
4. Add a disposable OATH/TOTP test account using a test secret that is never written to evidence.
5. Verify the generated code against the same test secret using the repository's TOTP test helper, without logging the secret or the live code.
6. Verify a wrong password fails closed and does not reveal whether an item exists.
7. Perform an Authenticator reset/remove on disposable data; confirm Vault items survive.
8. Verify the existing accounts and envelope are not deleted.
9. Export an encrypted archive using a test passphrase, re-import it into an isolated test location or disposable account, and verify round-trip integrity.
10. Do not claim Microsoft push/number-matching/passwordless support. If Entra OATH is permitted by the tenant, test one third-party OATH enrollment only; otherwise mark it `NOT_TESTED`/`OWNER_ACTION_REQUIRED`.

### Step 6 — lock, suspend, restart and failure behavior

1. Lock the screen; confirm the keyring locks and Vault/Authenticator require unlock again.
2. Unlock the screen; confirm the vault does not silently expose secrets.
3. Suspend and resume; confirm the suspend hook `nuxel-keyring-lock` re-locks the collection.
4. Restart `nuxel-http-bridge` and `nuxel-bridge`; confirm the provider reconnects and the vault remains locked or unlocks only under the owner's policy.
5. Kill a test client mid-request; confirm no secret leaks and the bridge remains healthy.
6. Toggle the Home/app permission or capability for a non-Vault app; confirm it cannot call keyring verbs.
7. Replay a Home token against Vault; it must be rejected (`identity_mismatch` or `permission_denied`).
8. Verify the `keyring-launcher.secret` is not exposed to the PWA, logs, argv or environment.
9. Confirm `nuxel-pwa-host` has the relay marker and the keyring owner remains UID 0 on the session bus.

### Step 7 — rollback and recovery validation

1. Inspect the rollback script and confirm it preserves the keyring, Secret Service items, Authenticator envelope, launcher secret and downloaded encrypted archives.
2. Do not run a destructive live rollback after the owner has real data. If the keyring is still empty/disposable, a rollback/forward test is allowed; otherwise use a disposable test keyring or mark the live rollback `NOT_TESTED`.
3. Record the exact rollback command and the backup it would use.
4. Verify the rollback does not remove `gnome-keyring`, `gcr3` or `libsecret` blindly. Package removal is a separate owner decision, never a generic rollback step.
5. If the vault is unavailable, confirm the UI shows a truthful error and does not fall back to localStorage, plaintext files or a fake success.

### Step 8 — regression checks

Re-run the 63000 suites after any deployment or fix. Also re-check:

- Home app registry and PWNAGE-72000 manifest fixes;
- bridge/API health and capability isolation;
- Vault/Authenticator Nuxtore bundles and signatures;
- package manifest and deploy artifact checksum;
- no secret values in logs, reports, screenshots or shell history;
- no keyring file content was read or modified unexpectedly.

---

## 4. Acceptance matrix

| Criterion | Required evidence | Allowed final state |
|---|---|---|
| Live file parity | SHA-256 source/live table | `INSTALLED` |
| Secret Service provider | bus owner PID/UID/EUID, package versions | `PHYSICALLY_VERIFIED` only after a live Vault operation |
| Keyring initialization | owner-created master password; Vault status `unlocked` | `PHYSICALLY_VERIFIED` |
| Vault create/edit/copy/delete | disposable item lifecycle, no secret leakage | `PHYSICALLY_VERIFIED` |
| Lock/unlock fail-closed | locked read denied; wrong password denied | `PHYSICALLY_VERIFIED` |
| Authenticator link/auto-unlock | consent link, gated unlock, reset isolation | `PHYSICALLY_VERIFIED` |
| TOTP/OATH | disposable test vector matches, secret never logged | `PHYSICALLY_VERIFIED` for OATH only |
| Microsoft push/passwordless | explicitly unsupported unless independently proven | `NOT_SUPPORTED` / do not claim |
| Export/import | encrypted round trip with test passphrase | `PHYSICALLY_VERIFIED` |
| Suspend/screen-lock re-lock | hook fires, vault relocks | `PHYSICALLY_VERIFIED` |
| Capability isolation | Home token replay rejected; unauthorized app denied | `HOST_TESTED` + live API test |
| Rollback preservation | keyring/envelope/launcher secret preserved | `HOST_TESTED` or `NOT_TESTED_LIVE` |
| No secret leakage | sentinel absent from logs/DOM/argv/evidence | `PHYSICALLY_VERIFIED` for tested paths |
| TWRP/reflash | not needed | state clearly in report |

Use `OWNER_ACTION_REQUIRED` for any step needing the owner's master password, real fingerprint/PIN interaction, physical suspend/resume or tenant-specific Entra consent. Do not stand in for the owner.

---

## 5. Deliverables

1. Re-verified source/live SHA-256 parity table.
2. Any safe source/test/deploy fix, with exact rationale.
3. Verified backup and deploy log, or a clear `NO_REDEPLOY_NEEDED` record.
4. Owner-assisted Vault initialization evidence (no secret values).
5. Vault lifecycle results with disposable data.
6. Authenticator/TOTP results and explicit unsupported-capability statement.
7. Suspend, lock, restart and permission-isolation results.
8. Encrypted export/import and rollback-preservation results.
9. Host regression results with exact commands, exit codes and counts.
10. Dated evidence bundle and final report.

---

## 6. Final response format

Return:

- **Executive result** — do not overstate.
- **Exact tested hardware/software** — model, kernel, boot ID, source HEAD, package versions.
- **What changed** — file-by-file, or `no source change needed`.
- **Live parity** — source vs installed hashes.
- **Vault/Secret Service state** — provider owner, initialization state, no secret values.
- **Physical results** — Vault, Authenticator, TOTP, suspend, lock and permissions.
- **Security findings** — fail-closed behavior, redaction, permission isolation, residual risks.
- **Test results** — commands, exit codes, pass/fail/skip counts.
- **Remaining blockers / owner actions** — exact and ordered.
- **TWRP answer** — explicitly `not required` for this mission.
- **Rollback** — exact command and tested/untested state.
- **Final status** — one of `FULLY_FIXED_AND_PHYSICALLY_VERIFIED`, `IMPLEMENTED_PENDING_OWNER_TEST`, `PARTIAL_IMPLEMENTATION`, `BLOCKED_EXTERNAL`, or `REGRESSION`.

If the only missing item is the owner's master password or a physical interaction, stop at `OWNER_ACTION_REQUIRED` with the exact action. Never invent a successful vault unlock, TOTP code, export, migration or rollback.
