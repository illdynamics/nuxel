# PWNAGE-63000 — Migration and recovery

## 1. What is being migrated

The current Authenticator already has an authenticated AES-256-GCM envelope in:

```
localStorage['nuxel-authenticator-envelope-v1']
```

That envelope is **not** moved, re-encrypted or deleted by this mission. The only
new state is one optional Secret Service item containing the Authenticator vault
passphrase. The TOTP account list remains inside the existing ciphertext.

The live envelope at baseline was 654 bytes; its schema is
`nuxel-authenticator-vault` version 1. The ciphertext and passphrase were never
read or logged by the implementation.

## 2. Pre-migration backup (owner action)

Before linking the passphrase:

1. Open Authenticator → **Import / export** → **Export encrypted vault**.
2. Store that JSON file somewhere the owner controls.
3. Keep the current Authenticator passphrase available.
4. Optionally also use Vault → **Backup** to create an encrypted Vault archive.
   The two archives are independent.

An export is useless without its passphrase. There is no plaintext export button
and no hidden recovery copy.

## 3. First-run Nuxel Vault keyring

1. Open **Vault** from the Nuxel launcher.
2. The first-run screen explains that GNOME Keyring is the store, that the master
   password protects the whole Nuxel keyring, and that losing it plus all encrypted
   backups makes the data unrecoverable.
3. Enter the master password twice (minimum 10 characters; common/repeated/digits-
   only passwords are refused).
4. Vault calls `keyring.initialize`. The provider creates the login keyring through
   `gnome-keyring-daemon --login --daemonize` (stdin only) and relabels the fresh
   collection **Nuxel Vault**.
5. The master password is not stored by Nuxel, the Bridge or the PWA. The UI clears
   the fields after the operation.

If the keyring already exists, the same action unlocks it; a wrong password leaves
it intact and locked.

## 4. Linking the existing Authenticator passphrase

This is the only migration step that touches the existing Authenticator setup.

1. Open Authenticator and unlock the existing vault manually with its current
   passphrase.
2. Go to **Security → Nuxel Keyring convenience unlock**.
3. Read the explanation: the passphrase will be stored in the OS keyring; anyone
   or any process that can use the unlocked keyring with Authenticator's granted
   access may be able to unlock the TOTP secrets.
4. Tick **I understand and explicitly opt in…**.
5. Enter the current Authenticator passphrase again and press
   **Save passphrase to Nuxel Keyring**.
6. The app verifies that passphrase against the existing envelope, stores the one
   named credential item, reads it back internally to verify a match, and only then
   reports **Linked**.
7. If the keyring is locked, unlock it first. If the provider is unavailable, the
   operation is refused and the old envelope/credential state is preserved.

No TOTP account is rewritten, re-encrypted or removed during linking.

## 5. Normal unlock behavior

- **Keyring unlocked + linked:** Authenticator may auto-unlock on open. It reads
  its own credential, unlocks the existing envelope, then drops the credential
  reference.
- **Keyring locked + linked/unknown:** Authenticator stays locked. The lock screen
  shows a **Nuxel Keyring** card. Unlocking the keyring is a separate credential;
  after a successful keyring unlock, Authenticator may auto-unlock.
- **Cancel / provider unavailable:** Authenticator remains locked and manual
  passphrase entry remains available.
- **Explicit Authenticator lock:** the app clears codes and in-memory key material
  but does **not** lock the whole OS keyring (other authorized services would be
  affected). The screen-lock path is what locks the keyring.
- **Screen lock / background:** the app clears OTP codes immediately; the keyring
  is locked by Home's `security.lock` path.

## 6. Removing the saved credential

Authenticator → Security → **Remove saved credential**.

- Deletes only the Authenticator credential item.
- Leaves the encrypted TOTP envelope and all TOTP accounts untouched.
- Manual passphrase unlock continues to work.
- If the keyring is unavailable, deletion fails closed and the credential remains.

Vault → Integrations shows linked/not-linked status but cannot read or delete the
credential; management stays in Authenticator.

## 7. Rotating the Authenticator passphrase

Authenticator → Import/export → **Re-key vault**:

1. Verifies the current passphrase and new passphrase policy.
2. Creates a new envelope with a fresh PBKDF2 salt and AES-GCM key.
3. Saves and verifies the new envelope **before** touching the keyring.
4. If linked, stores the new passphrase in the same one credential item.
5. If the credential update fails, deletes the stale credential and disables
   auto-unlock; the new passphrase still opens the vault and the owner can re-link.
6. The old passphrase no longer opens the new envelope.

If the new envelope cannot be saved, the in-memory state is rolled back to the old
envelope/key/accounts and the old vault remains active.

## 8. Reset options

### Authenticator-only reset

Authenticator → Import/export → **Delete the Authenticator vault and its saved
keyring credential**. Typed confirmation: `DELETE AUTHENTICATOR VAULT`.

- First attempts to delete the one Authenticator credential item.
- If the keyring is locked/unavailable, the reset is **refused** and the TOTP vault
  is not deleted, so a stale credential is not left behind.
- Then deletes `localStorage['nuxel-authenticator-envelope-v1']`.
- Never deletes Nuxel Vault items or unrelated keyring entries.

### Nuxel Vault reset

Vault → Security → **Reset Nuxel Vault items**. Typed confirmation:
`RESET NUXEL VAULT`.

- Deletes only items with `application=org.nuxel.Vault`, including the Nuxel meta
  marker.
- Does not delete the Authenticator credential or TOTP envelope.
- Does not delete the OS collection, other apps' items or the keyring file.
- The Nuxel Vault master password remains the keyring password.

## 9. Recovery matrix

| Lost / damaged | Result | Recovery |
|---|---|---|
| Nuxel Vault master password | Keyring cannot be unlocked | No cryptographic recovery. If an encrypted Vault archive exists, importing it into a new keyring requires that archive's passphrase and the owner's approval. |
| Authenticator passphrase, keyring credential removed | TOTP vault cannot be unlocked | No cryptographic recovery; restore an encrypted Authenticator envelope backup and use its passphrase. |
| Keyring credential item lost, Authenticator passphrase known | Manual unlock works | Re-link in Authenticator → Security. |
| Keyring collection/daemon lost, keyring file intact | Collection locked/unavailable | Unlock with the master password; if the file is gone, restore/import an encrypted Vault backup. |
| Encrypted backup lost | No offline copy | No cloud escrow; data remains only in the device keyring. |
| Keyring master password + all Vault backups lost | Vault data unrecoverable | None. This is stated before initialization. |
| Phone root compromise | All secrets exposed | Out of scope; not a hardware-backed store. |

## 10. Rollback and secrets

Software rollback (see DEPLOYMENT-AND-ROLLBACK.md) must preserve:

- `/root/.local/share/keyrings/` (the encrypted keyring database),
- the Authenticator localStorage envelope,
- any downloaded encrypted archives.

Rollback removes/disables the new app/bridge methods and restores the previous
Authenticator JS/manifest/service worker. It must **never** run
`rm -rf ~/.local/share/keyrings` or delete Secret Service items as a generic
rollback. The old manual Authenticator passphrase path remains usable.
