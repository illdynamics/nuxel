# PWNAGE-63000 — Threat model

## Assets

- Nuxel Vault item payloads: passwords, usernames, URLs, tags, secure notes.
- Authenticator TOTP seeds and its encrypted vault passphrase.
- The Nuxel Keyring master password (used only during an unlock operation).
- Encrypted backups and their export passphrases.
- Keyring metadata: collection presence/lock state, opaque item IDs.

## Trust boundaries

1. WebKit PWA (untrusted JS surface) → loopback HTTP Bridge (root).
2. Bridge → session D-Bus → GNOME Keyring (root user on this image).
3. GNOME Keyring → encrypted keyring file under `/root/.local/share/keyrings`.
4. User → master password/export passphrase (never stored by Nuxel).

## Threats and controls

### T1. Local attacker with physical access while the phone is locked

- Keyring collection is locked by Home's screen-lock path (`security.lock` →
  `Service.Lock`). Home's swipe gesture is **not** a keyring unlock; it only
  reveals Home.
- Vault/Authenticator clear in-memory records and secret DOM on lock/hide.
- Authenticator OTP ticker stops and code DOM is cleared.
- The keyring master password and all backup passphrases are separate credentials.
- Residual: a root-level physical attacker on this image can access the root
  session and the keyring files. Root compromise is total compromise. GNOME
  Keyring software encryption is **not** a hardware security module or TEE-backed
  key store.

### T2. Malicious/compromised PWA calling keyring APIs

- Keyring RPCs require a per-session token whose app id matches the body, an
  allowed `Origin`, the registry capability, and route proof.
- The working iframe path uses a **launcher-minted token**: the root-owned native
  host holds a per-device secret in a top-frame-only closure and exchanges a
  request from the exact iframe Home created for a token bound to that iframe's
  app id. A malicious iframe asking Home for a token gets a token for its own
  frame's app id, which the allow-list denies unless it is Vault/Authenticator.
- The generic `/auth/token` endpoint is self-issued; those tokens are rejected
  for keyring unless they also carry a Referer under the app's route.
- The loopback dev auth bypass is disabled for keyring RPCs.
- The generic bridge mock fallback never succeeds for `keyring.*`.
- Per-app verb allow-lists: Vault cannot read the Authenticator credential;
  Authenticator cannot list Vault items; Home can only status/lock.
- Residual: all PWAs share one origin/WebKit view. A same-origin iframe that
  executes code in another iframe's realm or manipulates the parent DOM can still
  act with that frame's authority. The launcher token removes the trivial
  `app_id`-in-JSON / `/auth/token` bypass but cannot create origin isolation on
  this architecture. CSP, no third-party scripts and source review reduce the
  attack surface; this residual is not hidden.

### T3. XSS in Vault or Authenticator

- CSP restricts scripts to same-origin, blocks objects, frames/base changes and
  external connections except the local bridge.
- No CDN, remote font, analytics or third-party script.
- Secret output uses `textContent`, never HTML interpolation. The Authenticator
  escapes issuer/account values; OTP digits use `textContent`.
- Keyring payloads are validated/bounded server-side and client-side.
- Residual: an XSS already executing in the app's origin can use that app's own
  token and capability. This is why the apps must remain small and dependency-free.

### T4. Bridge process compromise / API endpoint exposure

- HTTP listener is `127.0.0.1` only.
- Keyring identity/capability checks are in the root HTTP process, not the UI.
- No arbitrary D-Bus proxy, arbitrary destination/method, arbitrary file path or
  shell command is exposed by the keyring namespace.
- Request size and item counts are bounded; prompts/timeouts are bounded.
- Errors are structured and do not include D-Bus payloads or exception text.
- Residual: the HTTP bridge runs as root on this image (documented kernel/socket
  constraint for the existing API). A root compromise of that process can reach
  root-owned keyring files; this is a platform limitation, not hidden by the UI.

### T5. Secret Service unavailable, crashed, replaced or locked

- Every keyring call returns `provider_unavailable`, `timeout` or
  `collection_locked`; no mock success, no plaintext fallback.
- Vault and Authenticator stay locked and show a visible error.
- Status is re-read after daemon replacement/resume; a stale session causes a
  single fresh `OpenSession` retry, then a structured error.
- A wrong master password leaves the collection intact and locked.

### T6. App backgrounded with secret DOM still rendered

- `visibilitychange` with `document.hidden` and a live vault locks immediately.
- `pagehide` clears secret state.
- Vault clears item lists, search, editor fields, generator output and detail
  panels; Authenticator clears codes, code cache and ticker.
- Clipboard references are dropped.

### T7. Clipboard history/sync capturing passwords or OTPs

- Copy is explicit user action only.
- After 30 s the app reads the clipboard back and clears it **only if it still
  equals the exact value the app copied**. A newer clipboard value from another
  app is never erased.
- If the clipboard cannot be read back, it is not cleared (fail safe).
- Toasts say “copied” but never include the value.
- Residual: OS clipboard managers/history/sync may capture a value before the
  30 s clear. The UI cannot control third-party clipboard history.

### T8. Debug logs, tracebacks, journal, argv, crash dumps, screenshots

- D-Bus secret payloads, passphrases, OTP values and base32 seeds are never logged.
- Keyring audit lines contain app id, verb, status code and elapsed ms only.
- The master password is passed to `gnome-keyring-daemon` on stdin, never argv or
  environment.
- Exceptions in secret paths are reduced to a class name/status; no payload text.
- Test suite asserts a unique secret is absent from captured keyring logs.
- Residual: WebKit/Python crash dumps and a root debugger can capture process
  memory. No software product can promise full memory erasure; copies are minimized.

### T9. Backup theft, weak export passphrase, tampering, KDF downgrade

- Export is always an authenticated AES-256-GCM archive under PBKDF2-SHA-256.
- Fresh 16-byte salt and 12-byte IV per export; minimum 210k iterations.
- Import rejects plaintext items, unknown schema/version, weakened KDF, bad salt/
  IV/ciphertext, unknown item fields and oversized fields.
- The export passphrase is never written into the archive.
- Import fully authenticates and validates before merge/replace; replace requires
  an explicit encrypted-backup acknowledgement.
- Residual: a weak export passphrase can be brute-forced offline. The UI refuses
  obvious weak/short passphrases but strength is ultimately the owner's choice.

### T10. Old encrypted Authenticator envelope left behind during migration

- The existing envelope is **not moved or deleted** by migration. It remains the
  single source of truth in localStorage ciphertext.
- Linking stores only the passphrase in the keyring after explicit consent.
- The envelope is still required for manual unlock and for every auto-unlock.
- A pre-link encrypted backup can be downloaded from the existing export action.
- Rollback preserves the envelope and keyring data.

### T11. Malicious Nuxtore bundle or forged app identity

- Nuxtore bundles are content-addressed; catalog entries carry SHA-256 and Ed25519
  signatures regenerated by the official staging tool.
- The installed registry is served from `/etc/nuxel/app-registry/`; keyring
  capability checks read the same registry.
- A forged `app_id` in JSON does not pass the token/referer/origin/capability check.
- Residual: the repository currently uses a published **dev fixture** signing key
  for beta catalogs. It is not a production trust anchor. Production must use a
  key whose private half never enters the repository.

### T12. User forgets keyring master password or loses backups

- There is no recovery key, no cloud escrow and no hidden reset.
- The UI states this before first initialization and in backup settings.
- Losing the master password and all authenticated backups means the data is
  unrecoverable; this is cryptographic, not a policy choice.
- Authenticator manual passphrase remains a separate recovery path for TOTP if
  only the keyring credential is lost.

## Mandatory control checklist

| # | Control | Where |
|---|---|---|
| 1 | No plaintext secrets in persistent browser storage | Vault/Authenticator source guards; only ciphertext envelope in localStorage |
| 2 | Secret Service is the persistent Vault store; no silent plaintext fallback | `secret_service.py`, `keyring_api.py`, `bridge.js` fail-closed |
| 3 | Authenticator envelope remains authenticated/encrypted; credential only after opt-in | `authenticator.js`, `vault.js`, keyring scopes |
| 4 | Per-app authorization | `keyring_api.ALLOWED`, `check_identity` |
| 5 | Strict origin/app identity | token app binding + Referer route + registry capability |
| 6 | Bounded, typed, schema-validated, prompt-aware D-Bus requests | `secret_service.py` |
| 7 | Lock invalidates UI/key material; status revalidated after resume | `lockVault`, `visibilitychange`, 30 s poll |
| 8 | No raw secrets in logs/metrics/errors | audit logger + structured errors + tests |
| 9 | Encrypted exports by default | `archive.js`; no plaintext export button |
| 10 | Scoped destructive operations | `reset-vault` only Vault items; Authenticator reset deletes only its envelope + credential |
| 11 | No network calls for credentials/TOTP/analytics | CSP + source guards + no external assets |
| 12 | No hardware-backed claim | documented: GNOME Keyring software encryption only |

## Explicit non-claims

- Not a hardware security module, TEE, StrongBox or secure element solution.
- Not Microsoft Authenticator, not push/number matching, not passwordless/PRT,
  not device registration/Intune compliance, not passkeys.
- Not phishing-resistant TOTP.
- Not protection against root compromise of this image.
