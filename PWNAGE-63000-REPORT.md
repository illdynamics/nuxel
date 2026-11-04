# PWNAGE-63000 — Nuxel Vault & Keyring Manager — final report

## Implemented

- Nuxel Vault PWA: first-run/unlock, overview, logins, secure notes, CSPRNG
  generator, safe clipboard auto-clear, encrypted export/import, auto-lock,
  provider diagnostics, Authenticator integration status, scoped reset.
- Native Secret Service provider: `services/nuxel-bridge/src/secret_service.py`
  (GNOME Keyring, `org.freedesktop.secrets`, typed operations, bounded prompts/
  timeouts, no secrets in logs) and `keyring_api.py` (per-app scopes, rate limit,
  structured value-free errors).
- Authenticator integration: explicit opt-in link, keyring status/auto-unlock only
  while the keyring is unlocked, manual fallback, remove credential, transactional
  re-key, Authenticator-only reset, immediate lock/clear on hide.
- Launcher-minted identity for iframe PWAs: the native top-frame relay holds a
  per-device secret and mints a Bridge token for the exact iframe Home created;
  self-issued tokens still require Referer route proof. This was required because
  measured WebKit iframe fetches carry no Referer.
- S10+ packaging/session: `gnome-keyring`, `gcr3`, `libsecret` added to the
  verified package source and regenerated manifest; session activation env;
  `nuxel-http-bridge` session bus + narrow keyring write paths; suspend lock hook.
- Registries/catalog: canonical registry version 12 with 42 apps, Home/native
  copies, Nuxtore catalog/bundles regenerated and Ed25519-signed, registry and
  catalog verifiers pass.
- Entra guidance: truthful third-party software OATH/TOTP flow; push, number
  matching, passwordless/PRT, device registration, Intune and passkeys explicitly
  unsupported.
- Tests/docs/deploy/rollback artifact.

## Live S10+ proof

- `gnome-keyring-48.0-3.fc43.aarch64`, `gcr3-3.41.1-11.fc43.aarch64`,
  `libsecret-0.21.8.2-2.fc43.aarch64` installed.
- `org.freedesktop.secrets` owned by UID 0 on `/run/nuxel-wayland/bus`
  (the root-owned Nuxel Wayland session).
- Post-reboot services active: `nuxel-wayland`, `nuxel-http-bridge`, `nuxel-web`,
  `nuxel-bridge`.
- Vault API status: `{"success":true,"state":"not_initialized",...}`; the agent
  did not create a keyring or choose a master password.
- Vault launched from Home; `Issued launcher-bound token for app
  org.nuxel.Vault` followed by `keyring app=org.nuxel.Vault verb=status status=ok`.
- Authenticator launched from Home; launcher token issued; keyring status and
  credential status succeeded. Its UI showed the manual passphrase path and
  “Nuxel Keyring is not initialized. Open Nuxel Vault to create it.”
- Existing Authenticator envelope remains `nuxel-authenticator-envelope-v1`,
  654 bytes, ciphertext only.
- No kernel/bootloader/modem/partition writes.

## Access matrix

| App | Capability | Secrets |
|---|---|---|
| `org.nuxel.Vault` | `secrets:manage` | its own Vault items only |
| `org.nuxel.Authenticator` | `secrets:authenticator-unlock` | its one named credential only |
| `org.nuxel.Home` | owner lifecycle | `status`/`lock` only |
| any other app | none | denied |

## Owner steps

1. Open Vault, create the Nuxel Vault master password.
2. Add disposable entries and verify lock/unlock/copy/edit/delete.
3. Unlock Authenticator manually, open Security, opt in and save the passphrase
   to the Nuxel Keyring; verify auto-unlock only while the keyring is unlocked.
4. Remove/re-link/rotate/reset on disposable data; verify Vault items survive an
   Authenticator reset.
5. Entra: enroll only if the tenant permits third-party software OATH; verify the
   code on Microsoft's page. Never share the seed/OTP.
6. Test suspend/resume and physical screen lock.

## Tests

`31 passed` (pwnage63000 + Authenticator guards), Authenticator vault `39`,
TOTP vectors `32`, Vault archive/pwgen `19`/`12`, bridge fail-closed `13`,
registry `42 apps problems=0`, Nuxtore all `SIGNED_VERIFIED`, package manifest
`resolved 72/missing 0/pin mismatches 0`, live provider lifecycle `22/22`.

## Artifact

`release/pwnage63000/nuxel-pwnage63000.tar.gz` + `.sha256`

```sh
sha256sum -c release/pwnage63000/nuxel-pwnage63000.tar.gz.sha256
tar -xzf release/pwnage63000/nuxel-pwnage63000.tar.gz -C /x
cd /x/nuxel
SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa tools/pwnage63000/deploy-pwnage63000.sh root@10.20.30.16
```

Backup: `/var/backups/nuxel/p63000-20261103T111313Z` (verified SHA256SUMS).
Rollback: `/usr/lib/nuxel/rollback-pwnage63000.sh <backup>`; it preserves the
encrypted keyring, Secret Service items, Authenticator envelope and archives.

## Remaining gaps

- The image runs the graphical session and Bridge as root. GNOME Keyring software
  encryption is not a hardware-backed/TEE store; root compromise is total.
- Same-origin WebKit iframes are not isolated from each other; the launcher token
  removes the trivial app_id/`/auth/token` bypass but not same-origin DOM/realm
  attacks. Documented in THREAT-MODEL.md.
- The stock gcr prompt does not map on Phoc; the supported PAM login-stdin path is
  used by the Vault/Authenticator UI.
- Real master-password initialization, real Authenticator linking/auto-unlock,
  real Entra tenant enrollment and suspend/resume acceptance remain owner actions.
- No hardware-backed key storage is claimed.

---

## PWNAGE 60000–65000 completion addendum (2026-11-04)

Live revalidation: `org.freedesktop.secrets` is owned by `gnome-keyring-daemon`
inside `nuxel-wayland.service`; `org.gnome.keyring` is also present; the
default `session` collection is visible. `/root/.local/share/keyrings` is empty,
so the truthful state is `not_initialized` — the owner has not created the
master password. No secret was read or created. `tests/pwnage63000`: 25 passed.
