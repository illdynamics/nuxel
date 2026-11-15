# Nuxel S10+ — screen lock, Vault, fingerprint and NFC — 2026-11-13

Device: Samsung Galaxy S10+ (SM-G975F, beyond2lte), Nuxel 0.8.3-beta, kernel
4.14.253.  Work done over SSH (`root@192.168.178.167`) with the live userspace
path (`scripts/nuxel-deploy-live.py --apply`); no partition, kernel or firmware
image was written.  The phone was already booted into Nuxel when the session
started (TWRP was not active), so no reflash was required.

## Fixed and verified on the handset

### 1. The unexplained second "Enter PIN" (at least 6 digits)
After a correct unlock, the home/nav gate called
`NuxelSecurityLock.verifyUnlock()`, which opened a legacy text-input sheet
asking for a *second* PIN with a stale "At least 6 digits" hint.

* `verifyUnlock()` is now a pure authority check: it never creates a prompt.
  `locked:false` from the root bridge -> `{ok:true}`; locked -> `{ok:false}`
  and the lock surface keeps ownership.
* `promptSecret()` refuses to create the legacy sheet at all once the
  credential surface (`NuxelLockscreenAuth`) exists.
* Verified live: PIN 3838 -> `auth-result via=pin success=true` ->
  `unlock:complete`; no `#nuxel-lock-prompt` element exists afterwards.

### 2. PIN 3838 and the "1234"-style dead-lock trap
* `3838` is accepted (not a repeat/sequence), stored twice-confirmed and only
  as an scrypt verifier.
* Both the pattern-setup flow and the PIN flow send the same value twice, and
  the bridge repeats the refusal server-side (`pin_confirmation_required`,
  `pattern_confirmation_required`), so a typo can never be stored.
* Attempt policy is `unlimited` (no rate limiting, no lockout); verified that
  repeated wrong credentials still answer `invalid_credential` with
  `unlimited_attempts: true` and the correct code is always accepted.

### 3. Keypad registered every digit twice
A real press produced `pointerdown` and then the compatibility `click`, so
"3838" became "33883388".

* One press now appends exactly one digit (the click that belongs to a
  pointerdown is consumed; distinct fast presses are never collapsed).
* Verified with the host's trusted (real GDK) tap: 4 taps -> `pinLen 4`
  -> Unlock -> unlocked.

### 4. Pattern lock
* Responsive 3x3 matrix (CSS grid) instead of broken absolute geometry; nine
  penguin lock-head dots, a live trail that follows the finger (SVG polyline on
  the same box), trail turns red on rejection.
* Setup requires the pattern twice before it can be enabled.
* PIN button sits directly below the matrix and always works as fallback.
* Verified live: draw 0-4-8-5-2 -> trail points rendered -> server verifies ->
  `unlock:complete`.  Wrong patterns never lock the phone out.

### 5. Vault: "I set a password, pressed Close, and then could not unlock"
Three separate defects were found and fixed in `services/nuxel-bridge/src/`:

1. **Unlock mechanism.** gnome-keyring 48 on this image applies a stdin
   password only through `--login`.  `--unlock` consumes stdin but never
   completes ("unknown daemon error"); `--replace` never reads stdin outside a
   fresh login session.  Unlock now uses `--login` with the password on stdin
   only (never argv, never the environment, never a log), bounded in time.
2. **The verifier that made a fresh Vault unopenable.** `initialize()` wrote a
   "master-password-verifier" item into the collection it had just created and
   read it back; on this daemon that read fails, so setup reported "unknown
   daemon error" while the keyring file was already written.  The verifier now
   lives in a 0600 sidecar (`nuxel-vault-verifier.json`) stamped with the
   keyring creation time.  A verifier from a replaced keyring is ignored, never
   trusted.
3. **A listing crash hid the Vault.** Internal records (meta/verifier) have no
   `type`, and one `KeyError` aborted the whole item list.  Internal records are
   now skipped by schema; only real login/note items are returned.

Also added: structural detection of an unopenable keyring (no exported key
record -> no password can ever open it), byte-exact backup under
`/var/lib/nuxel/security/keyring-backups/`, replacement with a daemon-created
keyring bound to the new master password, and explicit status/error
distinction (locked vs. wrong password vs. provider fault).

Verified live through the Vault app itself (iframe, real token path):
status -> locked, unlock -> `screen-main active`, badge `unlocked`,
`lock-now` -> locked, unlock again -> main.  Wrong password ->
`invalid_credentials` / "the master password is not correct".

### 6. Live-deploy gap that hid all of the above
`tools/s10plus/a43/package-live.py` did not package `secret_service.py`,
`keyring_api.py`, `security_provider.py` or `fingerprint_provider.py`, so live
deploys never replaced the image's older copies.  All four are in the payload
now, and `tests/pwnage_a80` asserts it.

### 7. NFC kept working, with a debug window and a Test button
* Settings -> NFC has a read-only debug window: log, state, controller, result,
  UID, technology and NDEF summary, plus Test / Stop / Clear and a duration.
  The Test path only calls scan/read (never write).
* NFC is a per-app grant (`nfc`).  Screen lock, pattern/PIN/fingerprint and the
  Vault work do not touch the NFC service; `nuxel-nfcd` stayed active
  throughout.
* The Test button now names the real cause instead of blaming the card:
  `NFC_NOT_GRANTED` (grant it in Settings -> Permissions), `NOT_ENABLED`,
  `DEV_UP was not acknowledged` (controller firmware, documented below) or
  `NO_TAG`.

## Not possible on this image — measured, not assumed

### Fingerprint: the S10+ ultrasonic sensor cannot be matched from userspace
Evidence collected on the handset:

* kernel binds `fps_qbt2000`; `/sys/class/fingerprint/fingerprint` reports
  `QBT2000 / QCOM / type_check 7`, `position 13.77,0.00,...`;
* `/dev/qbt2000_fd` is never readable (non-blocking read: 0 bytes) and
  `/dev/qbt2000_ipc` yields 0 bytes: there is no frame/event path to a normal
  world matcher;
* the SPI node has no kernel driver bound (`/sys/bus/spi/drivers` has no
  qbt2000 driver entry) and no `/dev/spidev*` exists;
* the diagnostic knobs (`adm`, `wuhbtest`, `bfs_values`) are writable only by
  the TEE/sensor daemon context (`EACCES` even as root, SELinux permissive);
* `tzdev`/`tziwsock` exist, i.e. matching lives in Samsung's TEE, and no vendor
  HAL/seam (libfpsensor, vendor qbt HAL) exists anywhere in the Nuxel rootfs;
* the kernel loops `ldo:0,ipc:0,wuhb:0,tz:1,type:qbt2000,int:0` (sensor not
  powered, no IPC) and the result is `wuhb test complete rc=0, wuhb_en:0`.

Nuxel therefore cannot honestly read a finger.  A fabricated "match" or a
recorded "enrollment" that can never authenticate is a security lie and is not
implemented:

* fingerprint unlock requires `provider_ready` (a real secure provider);
* the lock screen never paints the scanner artwork without one, and says why,
  with the PIN button directly below it;
* Settings' "Set up fingerprint" is disabled until a provider is ready, and the
  page explains the TEE reason;
* enrollment requires the Vault to be set up **and** unlocked and guides to (or
  opens) the Vault when it is not; errors are explicit, never silent;
* the widget is stored as an HMAC-bound record in the Vault with a 0600 file
  when a provider does exist.

The fingerprint artwork (`assets/nuxel-fingerprint.png`, 512 px) is shipped and
already positioned by the surface over the S10+ under-display scanner region
(`SCANNER` box from the kernel `position` values), ready for the provider.

### NFC Test cannot read a card yet
The controller answers its bootloader but refuses `NCI DEV_UP`
(`NFC_DEV_UP_FAILED`), which is the missing/never-loaded NCI firmware blocker
documented in `nfc3.md`/`nfc4.md`: it needs an `s3fwrn5`-owned kernel revision
plus the firmware download.  This predates this work and is independent of the
security changes; the Test button reports it truthfully instead of a fake
success.

## Test gates
* `python3 tests/pwnage_a80/test_a80_lockscreen.py` — ALL PASS (surface,
  two-entry setup, unlimited attempts, Vault unlock mechanism, unopenable
  keyring guard, verifier stamping, listing, payload completeness, keypad
  one-press, no second prompt, fingerprint honesty, NFC debug read-only).
* `python3 tests/pwnage45000/test_pwnage45000.py` — ALL PASS.
* Pre-existing, unrelated failures in `launcher-registry-test.js` (registry
  ids/version) and the LED diag test reproduce with the earlier uncommitted
  work stashed; they are not caused by this change.

## Follow-up (A82) — owner feedback after the first fix

Live build `a82` (SW cache `v102-a82-lockscreen`), deployed over SSH with
`scripts/nuxel-deploy-live.py --apply` and verified on the handset.

### 1. The PIN still registered every digit twice — root cause found
The A81 dedup compared the click against the pointerdown's `pointerId`.  A real
press arrives as **pointerdown + touchstart + pointerup + touchend + click**,
and WebKit retargets the pointer events per contact (`pointerId` -1, 0, 1, …,
even 2147483647 on this kernel).  The compatibility click carries no
`pointerId` at all, so the key match never held: pointerdown appended the digit
and the click appended the **same** digit again.  Reproduced on-device with the
exact sequence: one press of "1" produced `"11"`, "3838" would have been
"33883388".  Longer touches made it worse: a held press was also counted by an
idle fallback and then again by its release.

Fix: the keypad now has exactly **one** activation handler — the click (release),
which WebKit delivers exactly once per press whatever the event family before
it.  Keyboard input keeps its own path.  Verified on the device: full touch
presses of 1, 3, 1, 3 produced `"1"`, `"13"`, `"131"`, `"1313"`; pointer+click
and click-only presses also produce one digit.  `tests/pwnage_a80/
keypad_press_simulation.js` (jsdom) drives every sequence from the device log
and runs from `test_a80_lockscreen.py`; static checks reject any return to
pointerdown activation.

### 2. The second "enter PIN" overlay — deleted, not hidden
`security-lock.js` no longer contains `ensurePrompt()` or any DOM builder for
the old sheet (`#nuxel-lock-prompt`, "Enter PIN", "At least 6 digits").
`promptSecret()` always resolves `null`; there is no path that can create it.
Credentials are entered only on the lock surface; the Vault password only in
the Vault's own password field.  Verified live: no such node exists.

### 3. "Set up pattern / PIN" on the lock screen — removed
The button is hidden, disabled and inert, `openSetup()`/`openPatternSetup()`
only return `set-credential-in-settings`, and the whole `#lockscreen-setup`
sheet is deleted from `index.html` (pattern/PIN changes only in
Settings → Security).  The lock surface no longer paints the top-centre
"Draw pattern / Enter PIN" title or its instructions (the element is hidden and
left empty; only the transient error line is ever shown).

Also fixed while verifying: Cancel on the keypad used to leave the keypad up
(it passed the transient effective mode); it now restores the authoritative
mode.  `manifest.json` cache_version now agrees with `sw.js`.
