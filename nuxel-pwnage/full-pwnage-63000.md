# FULL-PWNAGE-63000 — Nuxel Vault & Keyring Manager

**Mission:** Build a real, system-integrated Nuxel Vault / Keyring Manager and integrate it with Nuxel Authenticator so the Authenticator unlock credential can be securely stored and used for convenient, user-authorized unlock. Preserve and improve the existing TOTP implementation, including Microsoft Entra work/school accounts through standard OATH/TOTP where the tenant permits third-party software tokens.

**Target device:** Samsung Galaxy S10+ (SM-G975F, `beyond2lte`, Exynos 9820), current Nuxel Fedora-based image and Wayland/Phoc session.

**Repository baseline:** `nuxel-main (11).zip`, especially the existing Authenticator and S10+ image/build paths. The agent must first verify it is operating on the current checkout and current live image, not an old deployment backup.

**Do the implementation.** This is not a research-only request. Audit, design, implement, package, test, update registries/catalogs, produce a deployment artifact and rollback instructions. If a real Secret Service provider cannot be made operational on the S10+, fail closed and report the exact blocker; never substitute a fake keyring or plaintext file.

---

## 0. Non-negotiable mission outcomes

Deliver all of the following:

1. A polished first-party **Nuxel Vault** app in the Nuxel launcher, with a secure, native-backed keyring rather than a browser-only password list.
2. A system Secret Service implementation available to the actual S10+ user session, preferably GNOME Keyring (`org.freedesktop.secrets`) with `libsecret`/Secret Service client support, correctly activated and unlockable in the Nuxel Wayland session.
3. A usable Vault UI for creating, finding, viewing, editing, copying, deleting, importing and exporting password entries and secure notes. Include a strong password generator and safe clipboard behavior.
4. A dedicated, scoped **Authenticator integration** that stores the existing Authenticator vault passphrase inside the OS keyring only after the owner explicitly opts in. When the system keyring is unlocked, Authenticator may automatically unlock its existing encrypted TOTP vault. When the keyring is locked, the Authenticator must remain locked until the user unlocks the keyring or enters the Authenticator passphrase manually.
5. A safe migration path for the currently deployed Authenticator vault. Preserve the encrypted envelope and existing TOTP entries by default. The owner explicitly authorizes an Authenticator reset if necessary, but that permission is not permission to silently wipe other keyring entries, passwords, or unrelated application data.
6. A guided Microsoft Entra work/school-account enrollment path for **standard software OATH TOTP**. Be truthful that this is not Microsoft Authenticator push, number matching, passwordless phone sign-in, device registration or passkey functionality.
7. Complete security, regression, packaging, physical-device and recovery verification. No secret values in logs, crash reports, screenshots, telemetry, debug output, command-line arguments, URLs or service-worker caches.

### Definition of the product

Nuxel Vault is the user's on-device password/keyring manager. It is not a fake front end that stores passwords in `localStorage`, nor a web page that merely writes JSON files. The system Secret Service is the security boundary and authoritative secret store. The PWA/GTK UI is a client of a privileged, narrowly scoped native backend.

Nuxel Authenticator remains a focused TOTP application. It should not be rewritten into a different authenticator protocol. It gains a secure keyring-backed convenience integration and truthful Microsoft Entra OATH onboarding.

---

## 1. Confirmed repository findings — start here

The supplied source archive contains these exact paths and behaviors. Verify they still match the working tree before changing them.

### 1.1 Existing Authenticator implementation

- App source: `pwa/nuxel-apps/authenticator/`
- UI: `index.html`, `css/authenticator.css`
- Logic: `js/authenticator.js`, `js/vault.js`, `js/totp.js`
- Offline tests: `tests/test-vault.js`, `tests/test-totp-vectors.js`
- Browser QR decoder: `vendor/jsQR.js` and its license file
- Current app metadata: `app.json`, `manifest.json`, `sw.js`
- Entra guidance: `ENTRA-OATH.md`
- Nuxtore bundle: `pwa/nuxel-apps/nuxtore/catalog/bundles/org.nuxel.Authenticator-1.0.0.bundle.json`
- Existing source guard: `tests/pwnage49000/test_authenticator_p49000.py`

The TOTP implementation already contains RFC 4226/6238 HOTP/TOTP primitives and supports SHA-1/SHA-256/SHA-512, 6/8 digits, variable period, `otpauth://totp/` parsing and QR-based enrollment. Existing Authenticator tests include published RFC vectors and security guards. Preserve and extend this work; do not replace a functioning implementation with a new untested crypto library.

`js/vault.js` currently uses AES-256-GCM with a fresh 12-byte IV for every save, a 16-byte salt, PBKDF2-HMAC-SHA-256 (default 250,000 iterations, minimum 100,000), and an encrypted envelope. It rejects plaintext imports and enforces account validation. Do not weaken these properties.

`js/authenticator.js` currently stores the encrypted envelope under the `localStorage` key:

```text
nuxel-authenticator-envelope-v1
```

The passphrase is intentionally not stored by the present implementation. That is why it must be entered each time after the vault is locked. The secret-bearing TOTP account list is inside AES-GCM ciphertext, not a plaintext account list, but the envelope itself currently resides in the PWA's `localStorage`.

The Authenticator service worker currently caches its own app resources and the common bridge script. It must never cache passwords, TOTP codes, QR enrollment payloads, decrypted vault content or Secret Service results.

### 1.2 Existing keyring/package gap

- `images/config/packages.yml` contains `gnome-keyring` in the generic display-shell package list.
- The supplied `images/s10plus/packages-manifest.json` does **not** contain a `gnome-keyring` or `libsecret` package entry in its generated per-package list.
- Therefore, do not assume the working S10+ image has a running Secret Service simply because a generic package config mentions GNOME Keyring.
- The S10+ session already creates a D-Bus session bus using `dbus-run-session` in its session startup path. Trace the actual active `nuxel-session.sh` and compositor service used by the current image; do not patch a stale A29/A45 script if the active path is newer.

### 1.3 Nuxel integration contracts

- Canonical PWA/native app registry: `pwa/nuxel-common/app-registry.json`.
- Registry consumers include Home `pwa/nuxel-home/js/apps.js`, native shell registry, Bridge registry endpoint and installed `/etc/nuxel/app-registry/app_registry.json`.
- PWA registry entries must resolve to a real `index.html` and `manifest.json`; the manifest must define `nuxel.capabilities` and match the pinned Bridge version.
- Registry consistency verifier: `tools/s10plus/a33/verify-app-registry.py`.
- Nuxtore catalog: `pwa/nuxel-apps/nuxtore/catalog/nuxtore-catalog.json`, package source metadata, and per-app bundle manifests under `pwa/nuxel-apps/nuxtore/catalog/bundles/`.
- Bridge browser client: `pwa/nuxel-common/bridge.js`.
- Native backend: `services/nuxel-bridge/src/` (inspect `bridge.py`, `api.py`, `capabilities.py`, permission checks and current service lifecycle).
- D-Bus policies/configs: `configs/dbus/`.
- S10+ package generation/rootfs builder: `images/s10plus/packages-manifest.json` and `images/s10plus/build-phone-rootfs-inside-fedora.sh`; trace the actual source-of-truth that generates these artifacts.

Critical Bridge caveat: the browser bridge client has a generic development/mock fallback for unknown operations. Add explicit fail-closed behavior for every keyring/secret operation. If the native provider is unavailable, the PWA must receive an unavailable/error result, not `{success:true,mock:true}` and never pretend a password was saved.

---

## 2. Phase 0 — source-of-truth and baseline capture

Before implementation:

1. Confirm Git branch, commit, working-tree status and Nuxel version.
2. Determine the exact running S10+ image revision and compare it with the repository HEAD. Record any source/live drift.
3. Locate the active Wayland/Phoc unit, active user-session launcher, active D-Bus session setup and actual web app server/launcher used on the phone.
4. Confirm current package state with read-only checks:
   - `rpm -q gnome-keyring libsecret` (inside the actual phone rootfs/session as appropriate)
   - service/DBus owner for `org.freedesktop.secrets`
   - `busctl --user list` / D-Bus equivalent
   - `secret-tool` availability only as a diagnostic, not as the eventual secret-management interface
   - actual default collection state (locked/unlocked) without printing any secrets.
5. Read the Authenticator current localStorage envelope only as metadata/size/schema for baseline. Never print, copy into logs, or attach the ciphertext if it is unnecessary. Never attempt to read or guess the user's passphrase.
6. Run the current Authenticator tests and `test_authenticator_p49000.py`; record baseline.
7. Capture exact app registry, Nuxtore bundle and package-manifest generation commands.
8. Write `docs/pwnage-63000/BASELINE.md` with proven facts, missing components, tests and live-vs-source differences.

Do not proceed on assumed service availability. A working D-Bus session does not prove Secret Service is registered; an installed daemon does not prove it is activated; an activated service does not prove it can unlock a collection.

---

## 3. Phase 1 — design the system keyring architecture

### 3.1 Preferred backend: Secret Service

Use the freedesktop Secret Service API (`org.freedesktop.secrets`) provided by GNOME Keyring for this GTK/Phosh-oriented system, unless the active image already has a better fully supported provider. Use the standard D-Bus API and a supported client library such as `libsecret` where practical.

Documentation:

- Secret Service API: https://specifications.freedesktop.org/secret-service/latest/
- Secret Service overview: https://specifications.freedesktop.org/secret-service/latest/ch01.html
- GNOME Keyring project documentation: https://wiki.gnome.org/Projects/GnomeKeyring
- libsecret API documentation: https://gnome.pages.gitlab.gnome.org/libsecret/

Do not invent a new D-Bus secret protocol, roll a bespoke keyring file format, or implement a custom crypto algorithm. Do not call `secret-tool` with secrets in argv or environment variables. If `secret-tool` is used for a development smoke test, pass data through stdin and ensure shell history/process listings/logs cannot reveal it; production UI/backend must use a narrowly scoped API.

### 3.2 Native provider service / backend

Create a dedicated backend module under `services/nuxel-bridge/src/` (for example `secret_service.py` or an equivalent well-integrated module). Do not put D-Bus access or privileged filesystem operations in the PWA.

Required behavior:

- Connect only to the current user's session bus.
- Verify that `org.freedesktop.secrets` is owned by the expected user-session service.
- Discover the default collection and report whether it exists, is locked, is unlocked, or is unavailable.
- Create/open an explicit Nuxel collection if supported and appropriate; do not silently store in an unrelated collection.
- Support list/get/create/update/delete/lock/unlock operations with strict schema validation and timeouts.
- Handle Secret Service prompt paths correctly. If an operation returns a prompt object, invoke the prompt through the real D-Bus API, await its completion with a bounded timeout, and handle user cancellation. Never hang the Bridge request forever waiting for a prompt.
- Never log D-Bus secret payloads, D-Bus object secret bytes, passphrases, OTP values or base32 seeds.
- Zero mutable secret buffers where practical after use. Python/JS runtimes cannot promise full memory erasure; do not make such a promise. Minimize copies and object lifetimes.
- Do not expose a generic arbitrary D-Bus proxy or arbitrary item lookup to the web app.
- Restrict app access by validated Nuxel app ID, manifest capability and origin/route. The Authenticator may only request its own one named credential; it must not enumerate or retrieve the user's unrelated keyring passwords.
- The Vault app may manage its Nuxel Vault collection items, not arbitrary secrets owned by other applications.
- Apply request-size limits, schema validation, rate limits for failed unlock attempts where this can be done without weakening GNOME Keyring's own policy, and audit events that contain action/status but not values.
- Return structured, non-secret errors: `provider_unavailable`, `collection_locked`, `user_cancelled`, `item_not_found`, `permission_denied`, `timeout`, `invalid_request`.

Preferred bridge API namespace (adapt to existing Nuxel RPC conventions; do not add an untyped command endpoint):

```text
keyring.status
keyring.initialize
keyring.unlock
keyring.lock
keyring.list-items
keyring.get-item
keyring.create-item
keyring.update-item
keyring.delete-item
keyring.change-master-password   # only if supported safely by active provider
keyring.backup-status
keyring.authenticator-credential-status
keyring.authenticator-credential-store
keyring.authenticator-credential-get
keyring.authenticator-credential-delete
```

The names are a suggested RPC contract, not permission to blindly expose all operations. Split capabilities by use. `org.nuxel.Authenticator` should only receive its own `authenticator-credential-get/store/delete/status` operations. `org.nuxel.Vault` receives the CRUD methods for the Nuxel-owned collection. A different app must not invoke the Authenticator credential method by spoofing its JSON body.

If the current Bridge permission model requires a new capability enum, schema, policy and tests, add them in the same source-of-truth and update every consumer. Prefer a narrow `secrets:manage` for Vault and `secrets:authenticator-unlock` for Authenticator over a broad `secrets:*` capability.

### 3.3 Fail-closed behavior in the browser client

Update `pwa/nuxel-common/bridge.js` and the Bridge fallback behavior:

- Secret/keyring operations must never succeed in mock mode.
- An unavailable Bridge or missing Secret Service returns explicit `success:false`, `offline:true`, `state:"unavailable"` and a clear error.
- Never save secrets to `localStorage`, IndexedDB, Cache Storage, service worker cache or mock memory because a bridge call failed.
- No development fallback may create a fake “unlocked” collection or fake items.
- Tests must prove that disconnected Bridge + attempted save produces a visible error and zero persisted secret data.

### 3.4 Keyring daemon and user session lifecycle

Integrate the actual provider into the active S10+ image and session:

- Add the correct Fedora 43 ARM64 packages (at minimum verify `gnome-keyring` and `libsecret`; check whether the service requires any separate runtime packages such as PAM or GCR components). Resolve exact package names against the current trusted Fedora 43 metadata and the repository's package manifest generator.
- Add to the **S10+ actual package source of truth**, not only `images/config/packages.yml` if that file is for another target. Regenerate `images/s10plus/packages-manifest.json` through the official generator. Keep repository signature and fail-closed dependency policies.
- Ensure the daemon is activated once per user D-Bus session. Prefer the D-Bus service activation path or an explicitly supervised session component with correct environment (`DBUS_SESSION_BUS_ADDRESS`, XDG runtime dir, user identity). No duplicate daemon per PWA.
- Check whether `gnome-keyring-daemon --start --components=secrets` is appropriate for this image, and use the supported invocation/activation path for the exact installed Fedora build.
- Do not run the daemon as root if the user's session is unprivileged. Do not create a second D-Bus session solely for keyring access.
- Verify startup ordering: user D-Bus → Secret Service daemon → Nuxel Bridge → PWA launcher. Make readiness asynchronous and bounded; do not block boot waiting for a first-time user to create a keyring.
- Integrate screen lock, suspend, session end and shutdown. On screen lock, the keyring collection should be locked using a real Secret Service lock request after active in-memory app sessions are invalidated. On suspend/session end, lock and clear transient state. On app exit/timeout, lock the app UI and clear its own secret state; do not lock the whole OS keyring merely because a single app navigated away if that would break unrelated authorized system services.
- On resume, collection status must be re-queried; never assume the keyring remains unlocked.
- If the Nuxel session's current swipe-lock has no strong authentication gate, the keyring master password remains a separate credential. Never infer that dragging the penguin unlocks the keyring.

### 3.5 Native unlock prompt UX

Determine how the GNOME Keyring Secret Service prompt is presented in the actual Phoc/Wayland session. The prompt must be visible, reachable on the phone screen and styled consistently with Nuxel. If the stock prompt stack is unavailable or unsuitable, implement a small native GTK4/libadwaita unlock prompt connected to the provider's supported prompt flow.

Do not draw a fake unlocked screen in the PWA while the collection remains locked. Support cancel/back. Prompt must clearly say what is being unlocked (Nuxel Vault keyring), not display secrets. Never capture/store the entered master password outside the provider process and the short-lived unlock operation.

---

## 4. Phase 2 — Nuxel Vault app

### 4.1 App identity and visual design

Create `pwa/nuxel-apps/vault/` unless repository conventions indicate a native GTK app is more appropriate. Prefer a PWA front end plus native Secret Service backend if the current PWA runtime can enforce app ID/origin/capability scoping. If it cannot, build the UI as a native GTK4/libadwaita app instead of weakening access controls.

Suggested identity:

```json
{
  "id": "org.nuxel.Vault",
  "name": "Vault",
  "category": "security",
  "description": "Nuxel's on-device encrypted keyring and password manager",
  "network": "none",
  "cloud_sync": false
}
```

Use the established Nuxel penguin/8-bit visual language, but design it as a serious security product: clean hierarchy, clear lock state, high contrast, readable phone-sized controls, touch targets, no decorative animations that delay unlock, no secret values visible by default. Use the app's own icon assets and app metadata.

Required screens:

1. **Welcome / first initialization** — explain what the OS keyring is, where data is stored, recovery limitations and the fact that the master password is never recoverable by Nuxel.
2. **Unlock** — status, master-password input, show/hide toggle, cancel, attempt/error feedback without distinguishing secret contents, no passphrase retained in form fields after action.
3. **Overview** — keyring status, item counts by category, recently used entries (metadata only after unlock), security settings and Authenticator integration status.
4. **Logins** — search and browse saved credentials.
5. **Secure Notes** — encrypted notes, hidden in recent previews.
6. **Add/Edit entry** — title, optional URL/origin, username, password, notes, tags, category and favorite. Secret fields hidden by default.
7. **Password Generator** — secure random password generation.
8. **Authenticator integration** — shows whether Authenticator is linked; enables/disables credential storage; rotate/remove the stored Authenticator unlock secret; open Authenticator.
9. **Import / Export / Backup** — encrypted-only export by default and encrypted import with validation.
10. **Security / Keyring Settings** — lock now, auto-lock timeout, change keyring password where the actual backend supports it, reset Nuxel-owned keyring, backup reminders, provider diagnostics.

All flows must work on 360×760 logical portrait UI and on the current S10+ panel modes. No tiny desktop-only dialogs.

### 4.2 Data model and metadata privacy

Secret Service implementations may leave item labels and lookup attributes visible even when the secret payload is encrypted. Therefore:

- Do not place passwords, TOTP seeds, recovery codes, sensitive titles, personal names, usernames, email addresses, service URLs, bank names or notes in Secret Service lookup attributes or D-Bus logs.
- Use opaque random UUID identifiers and minimal fixed attributes, such as `application=org.nuxel.Vault`, `schema=nuxel-vault-item-v1`, `item_id=<random opaque id>`.
- Use generic item labels that do not disclose the service/account name. Show human-friendly metadata only after the collection is unlocked and the payload is decrypted in memory.
- Secret payload should contain versioned JSON or another validated binary format with `type`, `title`, `url`, `username`, `password`, `notes`, `tags`, `favorite`, `created_at`, `updated_at`, and optional non-secret UI metadata.
- Validate and bound every field; reject malformed, oversized, duplicate or unknown schema versions.
- Prefer one Nuxel-owned collection and an indexed encrypted payload model that can be searched in memory after unlock. Do not enumerate arbitrary items from the whole system keyring and display them as if Nuxel owns them.
- If separate Secret Service items are used, ensure only opaque IDs and app ownership are visible in item attributes; human metadata stays in secret payloads.
- No decrypted entry cache in localStorage, IndexedDB, service worker Cache Storage or browser history.

### 4.3 Password/security features

Implement:

- Secure password generation using `crypto.getRandomValues` or a native cryptographic RNG. Never use `Math.random()` for any security secret.
- Uniform character selection without modulo bias. Generate from selected character classes and guarantee requested classes without leaking bias.
- Configurable length, uppercase/lowercase/digits/symbols, ambiguous-character exclusion, and passphrase option only if a bundled/verified local word list is used.
- Strength feedback as a local estimate only; do not claim a password has or has not been breached unless a separately reviewed, privacy-preserving service is built later. This mission is offline-only; do not query breach databases.
- Copy username/password individually with explicit user action. Do not reveal a password after copy. Automatically clear the clipboard after a short timeout only if the clipboard still contains the exact value this app copied; never erase a newer clipboard entry from another app.
- Hide/re-mask secret fields on navigation, backgrounding, timeout and lock.
- Add/update/delete with a clear confirmation for irreversible deletion.
- Search over decrypted metadata only while the keyring is unlocked. On lock, clear search results and all decrypted metadata from the UI.
- No browser autofill injection, credential harvesting, keylogging or automatic form filling in this mission. Any future autofill requires a separate reviewed permission/portal design.

### 4.4 Import/export and backup

- Default export must be an **encrypted archive**. Use a documented, versioned format with authenticated encryption, per-export random salt and nonce/IV, strong KDF parameters appropriate to S10+ performance, and a portable recovery passphrase that is never written to the archive.
- Prefer a mature vetted crypto implementation already shipped and used by the project. Do not write a new cipher, KDF or password hash. Reuse the existing AuthVault AES-GCM envelope code where appropriate or use a reviewed libsodium/Argon2id implementation available in the image; test its ARM64 build and performance. Do not use Argon2id through an unverified/handwritten JS implementation.
- Include archive schema version, crypto/KDF identifiers, salt, nonce, ciphertext and integrity/authentication validation. Reject downgrade KDF parameters.
- Plaintext export must not be offered as the default. If compatibility import from CSV or another password manager is supported, show a clear warning, parse in memory, never write an unencrypted temporary file, and confirm successful encrypted import before clearing transient buffers.
- Import must validate all entries, reject duplicate IDs and maliciously large/invalid fields, and never overwrite the active vault until the imported archive is fully authenticated and the user approves merge/replace.
- Keep a timestamped encrypted pre-migration backup of the existing Authenticator envelope in an owner-controlled path or download flow, not an unencrypted archive. Never overwrite the only backup.
- Provide an understandable warning: losing the master password and all valid encrypted backups means the data cannot be recovered. No hidden recovery password or cloud escrow.

### 4.5 Auto-lock and lifecycle

- Configurable inactivity timeout with a conservative default (e.g. 2 minutes), plus “Lock now”.
- Lock when Nuxel reports device screen locked, system suspend, user logout, session teardown or shutdown.
- Re-lock after a failed unlock burst if the provider exposes equivalent controls; avoid implementing a weak custom rate limiter that can be trivially bypassed.
- On lock: clear decrypted records, decrypted search index, password generator output, clipboard references, cached bridge results and all DOM secret text; stop timers; cancel pending clipboard/timeouts; clear password inputs.
- Treat app `visibilitychange`, `pagehide` and Home/minimize events carefully. If an app is merely backgrounded, lock it after configured timeout or immediately according to security setting. Do not leave secrets rendered in a background WebKit surface.
- Ensure all sensitive DOM updates use `textContent`, not unsafe HTML interpolation.

---

## 5. Phase 3 — Authenticator / Vault credential integration

### 5.1 Required UX

Add a dedicated “Nuxel Keyring” or “Unlock with Nuxel Vault” section inside Authenticator's lock/setup and Security settings:

- `Use Nuxel Keyring for convenient unlock` toggle.
- Clear explanation: “This stores the Authenticator vault passphrase in the Nuxel system keyring. Authenticator can unlock automatically only while the keyring is unlocked. Anyone or any process that can use the unlocked keyring with this app's granted access may be able to unlock these TOTP secrets. Keep the keyring protected.”
- A Save/Link action requiring the user to enter the **current Authenticator passphrase** (or unlock the existing vault manually first).
- An explicit permission/consent step before storing the credential.
- Show accurate states: `Not linked`, `Linked — keyring locked`, `Linked — keyring unlocked`, `Provider unavailable`, `Credential missing`.
- Offer `Remove saved Authenticator credential` without deleting the TOTP account vault.
- Offer `Forget Authenticator vault` only as a separate destructive action with typed confirmation; this does not reset the entire Nuxel Keyring.

Do not store the Authenticator passphrase in localStorage, IndexedDB, cookies, URL parameters, browser autofill, environment variables or a plaintext file.

### 5.2 Secret item design and permissions

Store one named Secret Service item owned by the integration, with minimal opaque attributes:

```text
application = org.nuxel.Authenticator
purpose = vault-unlock-credential
schema = nuxel-auth-credential-v1
```

Do not expose the raw value to any other app. The Authenticator Bridge capability should only be usable by the verified Authenticator app identity, current Nuxel session and expected local origin. A PWA cannot gain access merely by putting `app_id` into a JSON body; verify the actual launch/runtime identity established by the native launcher/Bridge.

A successful get operation may return the credential only to the Authenticator WebKit process through its secure, authenticated Bridge call. Document the residual in-memory exposure honestly. Never return it through SSE, broadcast events, shared app state, telemetry or general-purpose status methods.

### 5.3 Unlock flow

When Authenticator opens:

1. Read the current vault envelope from its existing storage adapter.
2. Query only the status of its own saved keyring credential.
3. If the credential exists and the keyring is unlocked, retrieve it through the scoped API, invoke `AuthVault.unlock()`, then immediately clear input/value references and any bridge result object as far as JS permits.
4. If the keyring is locked, show “Unlock Nuxel Keyring to continue” with an action that opens the real keyring prompt. Do not repeatedly trigger prompts or spin the UI.
5. If the user cancels or keyring provider is unavailable, remain locked and offer manual passphrase entry (unless policy disables that option); do not fall back to plaintext storage.
6. Manual passphrase unlock remains supported for recovery and offline fallback. The user may opt to save the entered passphrase in the keyring after successful unlock.
7. On screen lock, session end, suspend, configured timeout, app lock or keyring lock event, clear code cache and re-lock the Authenticator in-memory state. Never leave live OTP codes visible on a locked display.

### 5.4 Save/rotate/remove flows

- Linking: require successful Authenticator vault unlock with the current passphrase; create the Secret Service item; read it back only to verify a match; do not print value. Do not set `linked=true` until service confirms item creation.
- Rotation: on Authenticator passphrase change, verify the old password, create a new encrypted vault envelope with a fresh salt and GCM IV, update the keyring item only after the new envelope is durably saved, and use a recoverable transaction/backup so a failed step cannot leave the user locked out.
- Removal: delete only the Authenticator-owned credential item; leave the encrypted TOTP envelope untouched, so manual passphrase unlock still works.
- Reset: delete the Authenticator envelope and Authenticator credential only after explicit owner confirmation. Do not delete all Secret Service collections or the Nuxel Vault password items.
- If Secret Service is unavailable during a change, preserve the old working envelope and old credential and report that the operation did not complete.

### 5.5 Existing vault migration

The current vault is already AES-GCM encrypted in localStorage. Implement migration without assuming the passphrase is known by code:

1. Detect the existing `nuxel-authenticator-envelope-v1` envelope.
2. Leave it in place until user unlock and integrity validation succeed.
3. Ask the owner to enter the existing Authenticator passphrase once.
4. Decrypt, validate every TOTP record, then create the new keyring credential only after explicit opt-in.
5. If moving the envelope storage itself is beneficial, keep a valid encrypted backup and use an atomic write/verify/commit process. The encrypted envelope may remain in app storage if it is still ciphertext and the threat model is documented; never make the account list plaintext.
6. Verify all account count/metadata and TOTP codes against the existing encrypted vault before switching the default.
7. Only after full success should the old ciphertext key be removed or marked migrated. Retain a rollback-capable encrypted copy through the first successful reboot and owner verification.

The owner has authorized removal/reset of the current Authenticator setup if necessary. This authorizes an implemented, clearly-confirmed **Authenticator-only reset option**, not silent deletion during image build or automatic wiping of the whole OS keyring. Prefer migration/reuse first. If current data cannot be opened because the owner does not know the current passphrase or the envelope is corrupt, explain that cryptographic recovery is impossible and allow the owner to create a new Authenticator vault after a clear destructive confirmation.

---

## 6. Phase 4 — Microsoft Entra work/school account support

### 6.1 What is possible

The existing TOTP engine can support Microsoft Entra work/school accounts when the tenant allows third-party software OATH/TOTP. Microsoft documents OATH TOTP as an open standard and says third-party OATH TOTP applications can be used; the tenant's Authentication Methods policy can disable third-party software OATH tokens.

Official references:

- Microsoft Entra OATH token documentation: https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-oath-tokens
- Manage third-party software OATH tokens: https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-mfa-manage-oath-tokens
- Authentication methods policy guidance: https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-authentication-methods-manage
- Microsoft Authenticator method overview: https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-authenticator-app

Nuxel Authenticator can generate the same **standard OATH TOTP verification codes** when Microsoft Entra provides a software-token QR code or Base32 seed and the tenant permits third-party OATH. The user must complete Microsoft's enrollment/verification flow.

### 6.2 What is not the same as Microsoft Authenticator

Do not claim the Nuxel app is Microsoft Authenticator, and do not claim support for:

- Push approvals/notifications or number matching.
- Passwordless phone sign-in / Authenticator broker flow.
- Entra device registration or Primary Refresh Token (PRT) issuance.
- Microsoft Authenticator passkeys, device-bound keys or attestation.
- Intune device compliance claims or Conditional Access device trust.
- Any Microsoft proprietary registration or push protocol.

Do not reverse-engineer, imitate, spoof or impersonate Microsoft Authenticator device registration/push. These are not required to generate a standard TOTP code and would create a misleading/security-sensitive integration.

### 6.3 Enrollment UX

Add an `Add Microsoft work or school account` guided option:

1. Explain that this is **third-party software OATH/TOTP**.
2. Open or display the official Entra Security Info enrollment instructions; do not ask the user to enter their work password into Nuxel Authenticator.
3. Direct the user to sign in to the organization's approved security-info portal on a trusted device/browser and choose an option that explicitly permits a third-party authenticator/software OATH token (wording depends on tenant setup).
4. Scan the presented QR code with the app camera, import a QR image, paste a standard `otpauth://totp/` URI, or enter the Base32 seed manually.
5. Parse issuer, account, secret, algorithm, digits and period; show the metadata preview and ask the user to confirm before saving.
6. Default Microsoft Entra values only when actually supplied by the QR/setup URI; do not blindly override issuer/algorithm/period. Entra's common OATH TOTP profile is SHA-1 with 6 digits and a 30- or 60-second period, but honor the actual enrollment parameters.
7. Ask the user to enter the current generated code into Microsoft's enrollment page to confirm registration; Nuxel itself cannot verify tenant acceptance.
8. Show clear help if the organization disables third-party OATH, requires push/number matching, device registration or a phishing-resistant method. Direct the user to IT for an approved method.

Add an `ENTRA-OATH.md` update that distinguishes TOTP from Microsoft Authenticator push. Include tenant policy caveat and the fact that standard TOTP is not phishing-resistant and may not satisfy a Conditional Access policy requiring phishing-resistant authentication.

### 6.4 TOTP integrity

- Preserve RFC 4226/6238 vectors and test all supported algorithms/digits/periods.
- Verify URI parser edge cases, QR image/camera parsing and issuer/account handling.
- Use correct `otpauth://totp/` URI path/query parsing and URL-decoding; reject HOTP URIs rather than interpreting them as TOTP.
- Detect poor device clock synchronization and show a non-secret time warning. Do not change system time automatically.
- Never claim “Microsoft accepted this code” unless the user completes and confirms the external flow.

---

## 7. Phase 5 — app registration, package and release integration

### 7.1 New Vault app registration

Add the app consistently to:

- `pwa/nuxel-apps/vault/` (or the selected native app source)
- `pwa/nuxel-common/app-registry.json`
- Native shell app registry source/consumer if required
- Installed `/etc/nuxel/app-registry/app_registry.json` generation
- `pwa/nuxel-apps/nuxtore/catalog/nuxtore-catalog.json`
- New bundle manifest under `pwa/nuxel-apps/nuxtore/catalog/bundles/`
- App icon/branding manifest and app inventory/feature matrix where generated
- Tests and app registry consistency checks

Use a stable app ID such as `org.nuxel.Vault` and capability(s) defined in `services/nuxel-bridge/src/capabilities.py`. Do not invent undeclared capability strings in the app manifest.

### 7.2 PWA manifest and service worker

If the selected frontend is a PWA:

- Manifest declares the correct app ID, Bridge version pin, exact capabilities, offline-first status and `network:none`.
- Service worker caches only static shell assets. Do not cache any `/api/` response, Secret Service payload, keyring item, decrypted vault page or OTP code.
- Bump the service-worker cache name to force a clean deployment of the new code.
- Ensure all content remains same-origin; no CDN, analytics, remote fonts or third-party scripts.
- Add restrictive Content Security Policy and safe DOM rendering. No untrusted URL execution.

### 7.3 Package and D-Bus integration

- Update the actual S10+ package manifest source with the correct `gnome-keyring`, `libsecret` and any verified supporting runtime packages.
- Ensure GPG/package repository verification and existing fail-closed dependency checks remain enabled.
- Regenerate package manifest and validate ARM64 package resolution.
- Add D-Bus service activation/config only as necessary; do not permit unrestricted cross-app access to Secret Service through broad D-Bus policy.
- Confirm the D-Bus policy does not block the Nuxel Bridge's user-session client, and that Flatpak apps are not inadvertently granted blanket secret-service access. Only apps with valid Nuxel authorization can use scoped Bridge operations.
- Confirm gnome-keyring service is launched exactly once and survives app launches without leaking the daemon into root/system scope.

### 7.4 Nuxtore integrity

Regenerate the app bundle file list, hashes, sizes and signatures through the official repository tooling. Do not hand-edit hashes or reuse an old signature. Update catalog version and descriptions. Confirm the Store actually installs/updates the new Vault app and the Authenticator update, and verifies the bundle before activation.

---

## 8. Phase 6 — security review and threat model

Create `docs/pwnage-63000/THREAT-MODEL.md` and address each of these threats explicitly:

- Local attacker with physical access while phone is locked.
- Malicious or compromised PWA trying to call keyring APIs.
- XSS in Vault or Authenticator.
- Bridge process compromise / API endpoint exposure.
- Secret Service provider unavailable, crashed, replaced or not unlocked.
- App backgrounded with secret DOM still rendered.
- Clipboard history/sync capturing copied passwords or OTPs.
- Debug logs, Python tracebacks, system journal, process arguments, crash dumps and screenshots exposing secret data.
- Backup file theft, weak export passphrase, ciphertext tampering, KDF downgrade.
- Old encrypted Authenticator envelope left behind during migration.
- Malicious Nuxtore bundle or forged app identity.
- User forgets keyring master password or loses backups.

Mandatory controls:

1. No plaintext secrets on persistent browser storage.
2. Secret Service is the persistent source for Vault data; no silent plaintext fallback.
3. Authenticator's existing encrypted envelope remains authenticated and encrypted; store its unlock credential only in Secret Service after explicit opt-in.
4. Per-app authorization; Vault cannot inspect unrelated application keyrings; Authenticator can access only its own unlock credential.
5. Strict origin and application identity validation; a caller-supplied app ID is not proof of identity.
6. D-Bus requests are bounded, typed, schema-validated and prompt-aware.
7. Lock invalidates UI and key material; status is revalidated after resume.
8. No raw secret values in logs/metrics/SSE/error text.
9. All file exports encrypted by default.
10. Destructive operations are scoped and require informed confirmation.
11. No network calls from Vault or Authenticator for credentials, TOTP seeds, passwords or analytics.
12. Do not promise hardware-backed storage/TEE protection unless a real hardware-backed provider has been discovered and tested. GNOME Keyring software encryption is not equivalent to a hardware security module.

No “security by UI” only: authorization must be enforced in the backend and service policy. Hiding a button is not access control.

---

## 9. Phase 7 — automated tests

Build deterministic offline tests with a test-only Secret Service fake/provider abstraction. The fake must be impossible to select in the production image and must never claim to be a real keyring during owner testing.

### 9.1 Provider/backend tests

- Provider not installed → unavailable, no fake unlock.
- D-Bus not running → bounded error, no hang.
- Secret Service bus name absent → unavailable.
- Collection absent → first-run initialization path.
- Collection locked → locked status; `get` cannot read secret.
- User cancels prompt → cancelled, remains locked.
- Unlock success → status changes only after provider confirms.
- Wrong keyring password → no secret returned, no item created.
- Item CRUD → exact item scope; unrelated items remain invisible.
- Item delete → deletes only selected Nuxel-owned UUID.
- D-Bus timeout/service crash → UI remains responsive and locked.
- A different app ID cannot call Vault or Authenticator secret RPCs.
- Spoofed JSON `app_id` cannot bypass runtime identity verification.
- Bridge mock mode → every secret action fails closed.
- No passphrase or secret appears in stdout, stderr, logs, exceptions or audit events.

### 9.2 Vault app tests

- First-time setup and keyring collection creation.
- Wrong password / cancelled unlock / re-lock.
- Add/edit/delete login entries and secure notes.
- Password generation uses CSPRNG and never `Math.random`.
- Clipboard failure never exposes secret in toast/error text.
- Clipboard auto-clear does not remove a different later clipboard value.
- Search works after unlock; results are cleared on lock.
- Secret text is never present in localStorage, IndexedDB, sessionStorage, Cache Storage, service worker cache or URL.
- Encrypted export/import, tamper detection, wrong export passphrase, schema downgrade rejection and interrupted import rollback.
- Reset Nuxel Vault does not delete Authenticator data unless separately confirmed, and does not wipe unrelated OS keyring entries.

### 9.3 Authenticator integration tests

- Existing RFC vector tests continue to pass.
- Existing vault tests continue to pass, including fresh GCM IV and plaintext import rejection.
- Existing encrypted envelope migrates with correct passphrase.
- Wrong passphrase refuses migration and leaves current envelope unchanged.
- Save-to-keyring requires explicit consent and successful vault unlock.
- Auto-unlock works only while the real test provider is unlocked.
- Keyring locked → Authenticator remains locked.
- Removing stored credential preserves encrypted TOTP vault for manual unlock.
- Authenticator reset removes only Authenticator envelope and its one named keyring item.
- Passphrase rotation updates both encrypted envelope and keyring credential transactionally.
- App lock/screen lock clears code cache and UI.
- Existing QR camera and QR image import tests remain valid; camera tracks stop on lock/pagehide/visibility change.
- No fetch/XHR/WebSocket/outbound external traffic added to Authenticator or Vault.

### 9.4 Microsoft Entra/TOTP tests

- Import valid `otpauth://totp/` URI from Entra-style issuer/account labels.
- Preserve exact algorithm/digits/period values in URI.
- Accept valid Base32 secret; reject malformed/too-short secret as existing policy requires.
- Reject `otpauth://hotp/`.
- Show correct setup steps and third-party OATH tenant policy caveat.
- UI must not show a “Push enabled”, “Microsoft Authenticator registered” or “Device registered” claim.

### 9.5 Registry/build tests

- App registry verifier passes.
- New Vault manifest capability/version pin resolves.
- Nuxtore generated bundle file list, file sizes, SHA-256 and signature verify.
- ARM64 package manifest resolves `gnome-keyring`/`libsecret` with trusted metadata.
- Rootfs package audit confirms expected binaries, D-Bus service files and libraries.
- No secret service daemon runs as root or duplicates per app.

---

## 10. Phase 8 — physical S10+ acceptance

A successful desktop/VM test is not sufficient. Run staged physical tests over the known safe Nuxel deployment path; do not flash the kernel/bootloader or touch modem partitions for this mission.

### 10.1 Keyring lifecycle

- Cold boot phone.
- Verify the D-Bus session and Secret Service name appear once.
- Open Vault; first-run initialize; set a strong master password.
- Create sample disposable entries (never use real work/bank passwords during tests).
- Lock Vault; verify entries are no longer visible in DOM or process-level app logs.
- Reopen, unlock and verify entries.
- Lock phone; verify keyring is locked and Vault/Authenticator surfaces do not display secrets.
- Unlock phone; confirm keyring remains locked until its own required unlock credential has been entered.
- Suspend/resume; check provider state and re-lock behavior.
- Reboot; confirm entries persist encrypted and provider works after startup.
- Kill/restart Bridge and daemon in a controlled test; no fake-success or data loss.

### 10.2 Authenticator linkage

- Back up the current encrypted Authenticator envelope.
- Enter the existing Authenticator passphrase manually.
- Link the credential to Nuxel Keyring only after clear consent.
- Lock keyring and reopen Authenticator: it must not display codes.
- Unlock keyring and reopen/refresh Authenticator: auto-unlock may occur according to the user's opt-in.
- Remove the Authenticator credential item: existing TOTP vault must still unlock manually.
- Re-link, rotate passphrase and verify codes continue to generate.
- Test an Authenticator-only reset on disposable/test data, verify other Vault entries remain intact.

### 10.3 Entra work account enrollment

Do not ask for or record the user's real work TOTP seed in repository evidence. Use a disposable test tenant/account if possible. Otherwise have the owner perform their own enrollment locally and report success without sharing QR/seed/code.

- Start official security-info enrollment.
- Select third-party/software OATH if tenant presents the option.
- Scan QR or enter setup data into Nuxel Authenticator.
- Confirm issuer/account, generate current code and type it into the Microsoft registration page.
- Verify sign-in using the newly registered TOTP method.
- Record only outcome and non-sensitive metadata (tenant policy state, algorithm/digits/period if not identifying), never the seed or OTP.

### 10.4 Performance

- Measure Vault open/unlock latency on S10+ for first unlock and later unlocks.
- Make the UI responsive during KDF and D-Bus prompt waits; use async calls and progress state, not blocking WebKit/GTK main loop.
- Avoid repeated full Secret Service scans; cache only non-secret item IDs while unlocked and invalidate on lock.
- Keep background CPU/polling low. No half-second poll loop for keyring state; subscribe to provider signals or bounded status refresh.

---

## 11. Rollout, backup and rollback

### 11.1 Safe migration rollout

1. Create a backup of modified source files and relevant persistent app configuration.
2. Generate a signed build/release artifact using existing Nuxel build mechanisms.
3. Install required RPMs into staged rootfs; verify package provenance.
4. Install Vault app, update Authenticator app and update registry/catalog/cache versions.
5. Run offline tests and rootfs tests before touching live phone.
6. Deploy to S10+ over the existing safe path with console/SSH recovery available.
7. Verify keyring provider and D-Bus activation before asking user to initialize keyring.
8. Verify existing Authenticator envelope remains readable and intact.
9. Only then enable the Vault launcher entry and optional Authenticator auto-unlock UI.
10. Record on-device acceptance and produce a final report.

### 11.2 Rollback

Rollback must:

- Remove/disable new Vault app and new bridge methods cleanly.
- Stop the new keyring startup hook only if necessary; do not delete the user's keyring collection automatically.
- Restore old Authenticator JS/manifest/service-worker code and old cache version safely.
- Preserve the encrypted Authenticator envelope and any Nuxel Keyring database/backup. Do not wipe user secrets during software rollback.
- Keep the old manual Authenticator passphrase unlock path functional.
- Never run `rm -rf ~/.local/share/keyrings` or remove all D-Bus Secret Service contents as a generic rollback.
- Include exact package remove/retain decisions and how to re-enable the previous behavior.

---

## 12. Deliverables

Create/update all of the following in the repository:

- `pwa/nuxel-apps/vault/` (or chosen native app tree) with complete production UI, metadata, icons, service worker and tests.
- Authenticator keyring integration, UI, updated docs and migration flow.
- Native Bridge Secret Service provider and narrowly scoped API methods.
- Capability, permission, D-Bus and session activation integration.
- Correct S10+ package manifest source and generated package manifest including verified keyring dependencies.
- Updated app registry and all mirrored consumers.
- Updated Nuxtore catalog and properly regenerated bundle manifest/signature.
- Tests for provider, bridge, Vault, Authenticator, Entra TOTP, registry, package integration and service lifecycle.
- `docs/pwnage-63000/BASELINE.md`
- `docs/pwnage-63000/ARCHITECTURE.md`
- `docs/pwnage-63000/THREAT-MODEL.md`
- `docs/pwnage-63000/MIGRATION-AND-RECOVERY.md`
- `docs/pwnage-63000/TEST-RESULTS.md`
- `docs/pwnage-63000/DEPLOYMENT-AND-ROLLBACK.md`
- A complete deployable patch/archive with exact path, SHA-256 and install command/prompt for the user's agent.

Final agent response must include:

1. What was actually implemented (not merely researched).
2. Which keyring provider/package was installed and the proof it owns `org.freedesktop.secrets` on the S10+.
3. Which app IDs/capabilities can access which secrets.
4. How the owner links the existing Authenticator passphrase and enables/disables auto-unlock.
5. What Microsoft Entra flow is supported and which features are explicitly unsupported.
6. Test results and any tests requiring owner action.
7. Exact build/deploy artifacts and checksums.
8. Backup and rollback procedure.
9. Any remaining gaps with evidence.

---

## 13. Hard prohibitions

- No passwords, OTP seeds, recovery codes or authenticator passphrases in plaintext localStorage, IndexedDB, cache, cookies, files, environment variables, process arguments or debug logs.
- No fabricated/mock keyring success in production.
- No storing the keyring master password inside the keyring itself.
- No app-wide unrestricted `org.freedesktop.secrets` access through a generic Bridge method.
- No direct file parsing/modification of GNOME Keyring's internal database.
- No custom cryptography or unaudited homemade KDF/cipher.
- No silent data wipe, no full-keyring reset when the user asked to reset Authenticator, and no loss of the old encrypted envelope until a new state is proven.
- No false claim that Nuxel Authenticator is Microsoft Authenticator or can perform Microsoft push approval/number matching/passwordless registration.
- No sending passwords, seeds, TOTP codes or metadata to external services.
- No disabling secure boot/image integrity/package signature checks as a convenience.
- No privileged raw shell command from the PWA and no D-Bus proxy that accepts arbitrary destinations/methods.

**Priority rule:** a safe, working Secret Service-backed Vault with manual unlock is better than an “automatic” convenience feature that weakens the keyring. A functioning third-party OATH TOTP work account is better than pretending to emulate all of Microsoft Authenticator. Implement the strongest real features the S10+ can support and clearly label the boundary.
