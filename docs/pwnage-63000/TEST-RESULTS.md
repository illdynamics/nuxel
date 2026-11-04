# PWNAGE-63000 — Test results

Date: 2026-11-03. Target: Samsung Galaxy S10+ `SM-G975F` (`beyond2lte`), Fedora
43 aarch64, kernel `4.14.253-gf7194c1d15ed-dirty`.

## 1. Offline / host test matrix

| Test | Result |
|---|---|
| `pytest tests/pwnage63000 tests/pwnage49000/test_authenticator_p49000.py` | **31 passed, 0 failed** |
| `node pwa/nuxel-apps/authenticator/tests/test-vault.js` | 39 passed, 0 failed |
| `node pwa/nuxel-apps/authenticator/tests/test-totp-vectors.js` | 32 passed, 0 failed |
| `node pwa/nuxel-apps/vault/tests/test-archive.js` | 19 passed, 0 failed |
| `node pwa/nuxel-apps/vault/tests/test-pwgen.js` | 12 passed, 0 failed |
| `node tests/pwnage63000/test_bridge_keyring.mjs` | 13 passed, 0 failed |
| `python3 tools/s10plus/a33/verify-app-registry.py` | `apps=42 problems=0 warnings=0 deferred=1 verdict=OFFLINE_TESTED_WITH_DEFERRALS` (the deferral is the pre-existing planned `privacy` app) |
| `python3 pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py` | all packages `SIGNED_VERIFIED`; Vault and Authenticator included |
| `python3 tools/s10plus/a33/verify-packages.py --offline` | `verdict=resolved resolved=72 missing=0 pin_mismatches=0` |
| `python3 -m py_compile` on bridge modules | pass |
| `node --check` on Vault/Authenticator/bridge JS | pass |

Coverage highlights:

- Provider unavailable / no D-Bus → fail closed, no fake collection.
- Collection locked → `get` refused, no secret returned.
- Wrong keyring password → `invalid_credentials`, data survives, no overwrite.
- Vault CRUD; unrelated application items invisible; delete only the selected UUID.
- Reset deletes only `org.nuxel.Vault` items; Authenticator credential and unrelated items survive.
- Authenticator credential store/get/delete; Vault cannot read/store it; Authenticator cannot list Vault items.
- Consent required before credential storage.
- Failed-unlock burst → `rate_limited`.
- Spoofed body `app_id`, missing token, wrong Origin, missing capability, and wrong route all denied.
- Launcher-minted token is accepted without a Referer; a self-issued token with no Referer is still denied.
- Disconnected browser bridge save → `success:false`, `state:"unavailable"`, `offline:true`; no mock, no localStorage write.
- Archive: fresh salt/IV, wrong passphrase, ciphertext tamper, KDF downgrade, plaintext archive, unknown/oversized fields.
- Password generator: CSPRNG, requested classes, ambiguity exclusion, no non-cryptographic PRNG.
- Source guards: no secret-bearing browser storage, no external CDN/analytics, service workers never cache `/api/`, `/rpc` or `/auth/`.

## 2. Live Secret Service lifecycle (real GNOME Keyring, isolated bus/HOME)

A 22-check integration test ran on the handset against the actual
`gnome-keyring-daemon` with a temporary bus and HOME (no owner data touched):

```
22 passed, 0 failed
```

It proved: fresh initialization and label `Nuxel Vault`; create/list/get/update;
metadata-only list; lock; read-while-locked refused; wrong password refused;
data survives; correct unlock; item survives; Authenticator store/get/status;
reset removes only Vault items; Authenticator credential survives reset;
Authenticator delete; no secret in provider logs.

## 3. Physical S10+ acceptance (performed)

- Deployed userspace to the real phone over Wi-Fi SSH (key `wicked_wqn_id_rsa`), then rebooted.
- Post-reboot services: `nuxel-wayland`, `nuxel-http-bridge`, `nuxel-web` all **active**.
- `gnome-keyring-48.0-3.fc43.aarch64`, `gcr3-3.41.1-11.fc43.aarch64`,
  `libsecret-0.21.8.2-2.fc43.aarch64` installed.
- `org.freedesktop.secrets` owned by UID 0 (the root-owned Nuxel Wayland session).
- Live API keyring status: `{"success":true,"state":"not_initialized", ...}`; no keyring was created by the agent.
- Spoof test: a Home-issued session token used with `app_id=org.nuxel.Vault`
  returned `identity_mismatch` / denied.
- Vault launched from Home; a launcher-minted token was issued and the keyring
  status call succeeded (`keyring app=org.nuxel.Vault verb=status status=ok`).
- Vault first-run UI verified from `nuxel-wl-snapshot` OCR: **“Create your Nuxel
  Vault keyring”**, master-password/repeat fields, recovery limitations.
- Authenticator launched from Home; launcher token issued; keyring status and
  credential-status calls succeeded. OCR verified: **“Unlock vault”**, manual
  passphrase path, and **“Nuxel Keyring is not initialized. Open Nuxel Vault to
  create it.”**
- The existing encrypted Authenticator envelope remains in place at
  `nuxel-authenticator-envelope-v1` (ciphertext only; not read or printed).
- Stock gcr prompt finding: `gcr-prompter` was activated and `PerformPrompt`
  observed, but no visible toplevel mapped in Phoc and a screenshot during the
  prompt was pixel-identical to the baseline. The supported PAM login path is used.
- Screenshot note: `grim` returned a black frame when the panel was off; the
  `nuxel-wl-snapshot` PPM path showed the real composited UI. This is a capture
  method difference, not a Vault failure.

## 4. Owner-action acceptance still required

These require the owner's own credentials/data and were deliberately **not**
performed by the agent:

1. Enter a master password in Vault and create the keyring.
2. Add disposable test logins/notes; verify lock, unlock, copy, edit, delete,
   search-clearing and clipboard auto-clear.
3. Reboot and confirm the encrypted Vault items persist and the keyring is
   locked until the owner enters the master password.
4. Manually unlock Authenticator with the existing passphrase, opt in, link it
   to the keyring, then test auto-unlock only while the keyring is unlocked.
5. Remove the saved credential and confirm manual Authenticator unlock still works.
6. Re-key Authenticator and confirm the keyring credential is updated; test the
   failure path if the keyring is unavailable.
7. Test an Authenticator-only reset on disposable data and confirm Vault items
   remain.
8. Enroll a real Entra work/school account only if the tenant permits
   third-party software OATH; do not share the seed or OTP in evidence.
9. Test screen lock / suspend / resume keyring locking and measure first-unlock
   and later-unlock latency on the S10+.

## 5. Evidence locations

- Baseline screenshot: `/tmp/p63000-baseline.png`
- Vault first-run OCR evidence: `/tmp/p63000-snap.png` (derived from `nuxel-wl-snapshot`)
- Authenticator lock/keyring OCR evidence: `/tmp/p63000-auth.png`
- Deployment record on device: `/var/lib/nuxel/p63000-deploy.json`
- Backup: `/var/backups/nuxel/p63000-20261103T111313Z`
- Live keyring logs contain only app/verb/status/timing, e.g.:
  `keyring app=org.nuxel.Vault verb=status status=ok ms=5`.
