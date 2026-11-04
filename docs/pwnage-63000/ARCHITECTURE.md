# PWNAGE-63000 — Architecture

## 1. Components

```
                    Nuxel Wayland session (Phoc, root on this image)
 ┌──────────────────────────────────────────────────────────────────────┐
 │  nuxel-pwa-host (WebKit)                                             │
 │    Vault PWA (org.nuxel.Vault)        Authenticator PWA              │
 │        │  window.NuxelBridge.keyring()    │                           │
 │        └──────────────┬───────────────────┘                           │
 │                       │ HTTP 127.0.0.1:8080 (loopback)                │
 │             nuxel-http-bridge (api.py, root)                          │
 │               │ identity + capability check                           │
 │               │ keyring_api.py (scoped verbs, rate limit, audit)      │
 │               │ secret_service.py (narrow Secret Service client)      │
 │               ▼                                                       │
 │       session D-Bus /run/nuxel-wayland/bus                            │
 │               │ org.freedesktop.secrets                               │
 │               ▼                                                       │
 │       gnome-keyring-daemon 48.0 (root session user)                   │
 │               │                                                       │
 │               ▼                                                       │
 │       /root/.local/share/keyrings/login.keyring  (encrypted at rest)  │
 └──────────────────────────────────────────────────────────────────────┘
```

There is no generic D-Bus proxy, no plaintext keyring file, no custom cipher and
no browser storage of secrets. `gnome-keyring` is the security boundary.

## 2. Secret scopes and app permissions

| App id | Capability | Allowed keyring verbs |
|---|---|---|
| `org.nuxel.Vault` | `secrets:manage` | `status`, `initialize`, `unlock`, `lock`, `list-items`, `get-item`, `create-item`, `update-item`, `delete-item`, `reset-vault`, `backup-status`, `diagnostics`, `authenticator-credential-status` |
| `org.nuxel.Authenticator` | `secrets:authenticator-unlock` | `status`, `unlock`, `lock`, `diagnostics`, `authenticator-credential-status/store/get/delete` |
| `org.nuxel.Home` | (owner surface, no secret capability) | `status`, `lock` only (screen-lock lifecycle) |

The Vault cannot read the Authenticator credential. The Authenticator cannot
enumerate Vault items. Home can only lock the collection. A different app cannot
invoke a keyring verb by putting another `app_id` in JSON.

### Identity check (backend)

Every `keyring.*` RPC requires all of:

1. a live per-session bearer token whose recorded `app_id` equals the request's `app_id`;
2. the current `Origin` exactly equal to the local PWA origin (`http://127.0.0.1:8000`);
3. for Vault/Authenticator, the registry entry granting the narrow capability;
4. route proof, one of:
   - **launcher-minted token** (the working iframe path): the token was issued
     by the native top-frame relay for the exact iframe the trusted Home page
     created, and carries `issuer=nuxel-launcher`; or
   - **self-issued token** (top-level/direct path): the token and the current
     request both carry a Referer path under the app's registered route.

The loopback "dev mode" auth bypass is explicitly **not** accepted for keyring
RPCs. The generic bridge mock fallback is never used for keyring operations.

#### Why the launcher token is needed

Measured on the S10+: WebKit does **not** send a `Referer` header for fetch
requests made from the PWA iframes used by the Home launcher. A Referer-only
policy therefore rejected legitimate Vault/Authenticator calls. The fix is a
trusted native relay, not a relaxed check:

```
iframe bridge.js
  -> parent.postMessage({type:'nuxel-keyring-token-request', nonce})
Home app.js (NuxelKeyringRelay)
  -> maps event.source to the exact iframe it created (WeakMap)
  -> window.postMessage({type:'nuxel-keyring-mint', app_id, nonce}) to itself
native top-frame-only user script (nuxel-pwa-host.c)
  -> POST /api/v1/auth/app-token with X-Nuxel-Launcher-Secret
  -> per-device secret in /etc/nuxel/keyring-launcher.secret (0600 root)
Bridge
  -> issues a token bound to that app_id with issuer='nuxel-launcher'
Home
  -> forwards the token to the requesting iframe only
```

The secret is read by the root-owned native host and the root-owned Bridge; it
is held in the top-frame user-script closure and is not a window property.
Iframes do not receive the top-frame script. A malicious iframe can ask Home
for a token, but Home uses `event.source` to look up that frame's registered app
id, so it receives a token for its own app id (which the allow-list denies if it
is not Vault/Authenticator). It cannot mint a token for another app id through
the normal path. Self-issued tokens still require Referer route proof.

Residual: all PWAs share one origin and one WebKit view on this image. A
same-origin iframe that actively executes code in another iframe's realm or
reaches the parent DOM can still act with that frame's authority; this is an
inherent limitation of the current same-origin WebKit architecture and is
documented in the threat model. The launcher token removes the trivial
"call `/auth/token` with another app_id" bypass.

## 3. Secret Service model

Provider: GNOME Keyring, `org.freedesktop.secrets`, on the root-owned Nuxel
Wayland session bus. The provider is D-Bus activated from the shipped
`/usr/share/dbus-1/services/org.freedesktop.secrets.service`.

### Collection

On a fresh device the first successful Vault initialization creates the provider's
`login` collection through the PAM-compatible login path and relabels it
**Nuxel Vault**. If a login keyring already exists, its label is left alone (so
Nuxel never renames another application's collection). Nuxel stores only items
whose attributes identify its own scopes and never enumerates unrelated items.

### Vault items

Attributes (visible to the provider, non-secret):

```
application = org.nuxel.Vault
schema      = nuxel-vault-item-v1
item_id     = <opaque random UUID hex>
```

Item label is always the generic `"Nuxel item"`. Human-readable title, username,
URL, notes and password are **inside the Secret Service secret payload**, never in
lookup attributes. The payload is versioned JSON:

```json
{"schema":"nuxel-vault-item-v1","type":"login|note","title":"…","url":"…",
 "username":"…","password":"…","notes":"…","tags":["…"],"favorite":false,
 "created_at":"…","updated_at":"…","id":"<opaque id>"}
```

A separate meta item (`schema=nuxel-vault-meta-v1`, `item_id=meta`) records only
first-initialization metadata.

### Authenticator credential

Exactly one item:

```
application = org.nuxel.Authenticator
purpose     = vault-unlock-credential
schema      = nuxel-auth-credential-v1
label       = "Nuxel Authenticator credential"
```

The secret value is the Authenticator vault passphrase. It is read back only
inside the Bridge to verify a write, compared with `secrets.compare_digest`, and
never logged, broadcast or returned to any app except the verified Authenticator.

## 4. Unlock model

The stock gcr prompt does not map on Phoc (see BASELINE.md). The supported
provider path is used:

1. Vault/Authenticator UI collects the **Nuxel Keyring master password**.
2. The Bridge verifies app identity and pipes the password to
   `gnome-keyring-daemon --login --daemonize --components=secrets` on **stdin**
   (never argv/environment/file).
3. `gnome-keyring-daemon --start --components=secrets` connects that daemon to the
   session bus.
4. The Bridge verifies `ReadAlias("default")` exists and the collection is
   unlocked. A wrong password leaves the keyring intact and locked; the daemon is
   stopped and the error is `invalid_credentials`.
5. The password reference is dropped; the UI clears the input.

Only the current bus owner is stopped, after verifying PID, UID 0, executable
name and the exact `HOME`/`XDG_RUNTIME_DIR` of this session. Stale
`gnome-keyring-daemon --login/--unlock` orphans from this same scope are cleaned
up. The daemon is never run in the system bus or as a second independent session.

## 5. Lifecycle

- **Boot**: the session script publishes `HOME`, `XDG_RUNTIME_DIR`,
  `WAYLAND_DISPLAY`, `GDK_BACKEND`, `XDG_SESSION_TYPE` to D-Bus activation and
  warms the `org.freedesktop.secrets` name in a bounded background job. The
  first Vault/Authenticator status call can activate the provider.
- **Screen lock**: Home's `security.lock` RPC also calls `keyring.lock`
  (`Service.Lock`). Home's swipe unlock does **not** unlock the keyring. The
  keyring requires its own master password.
- **App hidden/pagehide**: Vault and Authenticator clear decrypted state and
  secret DOM immediately. Authenticator clears live OTP codes.
- **Polling**: while unlocked, Vault and Authenticator perform a bounded 30 s
  status refresh. If the keyring becomes locked, the app locks its own UI.
- **Suspend/logout/shutdown**: the screen-lock path covers the normal Nuxel
  session; the provider's own collection lock is the authoritative state on
  resume. No code assumes the keyring stayed unlocked.
- **Daemon crash**: provider calls return `provider_unavailable`/`timeout`; apps
  remain locked. D-Bus activation can restart the daemon; status is re-read.

## 6. Bridge RPC contract

Token bootstrap endpoints (not part of the `keyring` namespace):

```
POST /api/v1/auth/token       {app_id}                 (generic, unauthenticated)
POST /api/v1/auth/app-token   {app_id, nonce}          (native launcher secret)
```

Namespace: `keyring`. All results are structured and value-free on error.

```
keyring.status
keyring.initialize                 {master_password, label}
keyring.unlock                     {master_password}
keyring.lock
keyring.list-items                 -> metadata only
keyring.get-item                   {item_id}
keyring.create-item                {item}
keyring.update-item                {item_id, item}
keyring.delete-item                {item_id}
keyring.reset-vault                {confirm:true}  (Vault-owned items only)
keyring.backup-status
keyring.diagnostics
keyring.authenticator-credential-status
keyring.authenticator-credential-store  {credential, consent:true}
keyring.authenticator-credential-get
keyring.authenticator-credential-delete
```

Error codes: `provider_unavailable`, `collection_locked`, `user_cancelled`,
`item_not_found`, `permission_denied`, `timeout`, `invalid_request`,
`invalid_credentials`, `rate_limited`, `provider_error`, `token_required`,
`identity_mismatch`.

There is no `change-master-password` implementation because GNOME Keyring does
not expose a safe standard Secret Service API for it; the UI reports that
limitation instead of using a private/unsupported keyring interface.

## 7. Vault UI

`pwa/nuxel-apps/vault/` is a vanilla ES-module PWA with:

- first-run/explanation, unlock, overview, logins, secure notes, generator,
  Authenticator integration status, encrypted backup/import, security/settings;
- CSPRNG password generator (rejection sampling, guaranteed classes, CSPRNG
  shuffle; no modulo bias, no non-cryptographic PRNG);
- clipboard copy with a 30 s clear that only erases the exact value this app
  copied and only if the clipboard can be read back;
- encrypted export/import (`nuxel-vault-archive`, AES-256-GCM,
  PBKDF2-SHA-256, fresh salt/IV, minimum 210k iterations, no plaintext export);
- auto-lock (default 2 min), lock-on-hide, manual lock, lock on keyring-locked
  status;
- no secret in localStorage/sessionStorage/IndexedDB/Cache Storage/URL/logs;
- service worker caches only same-origin GET shell assets and skips `/api/`,
  `/rpc`, `/auth/`.

## 8. Authenticator integration

- Existing AES-GCM envelope is preserved unchanged in
  `localStorage['nuxel-authenticator-envelope-v1']`.
- After explicit consent, the current passphrase is verified against the
  envelope and stored only as the one keyring credential item.
- On launch, status is queried. If linked and the keyring is unlocked, the
  credential is retrieved, the envelope is unlocked, and the credential value is
  cleared. If locked, the app remains locked and offers a keyring-unlock form
  plus manual passphrase entry.
- Manual unlock always remains available.
- Removing the credential deletes only that item; the TOTP envelope remains.
- Re-key saves the new envelope first, verifies it, then updates the credential.
  If the credential update fails, the old credential is removed and auto-unlock
  is disabled so a stale secret cannot be used.
- Authenticator-only reset deletes the envelope and its one credential item; it
  never calls Vault reset or deletes unrelated keyring data.
- Backgrounding locks immediately; OTP codes and the code cache are cleared from
  the DOM and memory.

## 9. Microsoft Entra

Only standard third-party software OATH/TOTP is supported. The app provides a
guided enrollment card, truthful tenant-policy caveat, QR/URI/manual entry, and
RFC 4226/6238 code generation. Push, number matching, passwordless/PRT, device
registration, Intune claims and passkeys are explicitly unsupported and not
imitated.

## 10. Packaging

- S10+ essential packages now include `gnome-keyring`, `gcr3`, `libsecret` in
  `tools/s10plus/a33/verify-packages.py`; `images/s10plus/packages-manifest.json`
  was regenerated with `--emit-manifest` and resolves aarch64 dependencies.
- `nuxel-http-bridge.service` points at the session bus and allows writes only to
  `/root/.local/share/keyrings` and `/run/nuxel-wayland/keyring`.
- `tools/s10plus/a45/nuxel-session.sh` publishes the activation environment and
  warms the Secret Service name.
- Canonical registry, Home `apps.js`, native shell registry, Nuxtore catalog,
  bundles and Ed25519 signatures were regenerated by the repository tools.
