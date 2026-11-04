# PWNAGE-63000 — Deployment and rollback

## 1. Exact deployment command

From the Nuxel checkout on the host:

```sh
cd /x/nuxel
SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
  tools/pwnage63000/deploy-pwnage63000.sh root@10.20.30.16
```

The script:

1. verifies the target is aarch64 Fedora with the Nuxel PWA host and docroot;
2. ensures `gnome-keyring`, `gcr3` and `libsecret` are installed (fail-closed dnf);
3. creates `/var/backups/nuxel/p63000-<UTC>/` and a verified `SHA256SUMS` of
   every file/directory it will replace;
4. stages only userspace payloads;
5. installs the Bridge modules, service unit, session script, suspend hook,
   Vault/Authenticator PWAs, Home registry/cache files, Nuxtore catalog and the
   canonical/native app registries;
6. creates `/etc/nuxel/keyring-launcher.secret` if absent (0600 root) and compiles
   `nuxel-pwa-host.c` on the target with gcc/GTK/WebKit, installing the new host
   only after a successful build;
7. `daemon-reload`, restarts `nuxel-http-bridge` and `nuxel-bridge`, and checks
   `nuxel-wayland`/`nuxel-web` activity;
8. exercises the scoped API with a Vault token and confirms a Home token cannot
   be replayed as Vault;
9. records `/var/lib/nuxel/p63000-deploy.json`.

It does **not** flash the kernel/bootloader, touch modem/partition data, create a
keyring collection, or ask for a passphrase.

A reboot (or a deliberate `systemctl restart nuxel-wayland`) is required to load
the new `nuxel-pwa-host` and the new session script. The user-visible final step
for this mission was a reboot.

## 2. Recorded live deployment

| Item | Value |
|---|---|
| Target | `root@10.20.30.16` (S10+ `beyond2lte`) |
| Pre-mission rollback backup | `/var/backups/nuxel/p63000-20261103T111313Z` (augmented with the original native host and Home files) |
| Backup verification | `sha256sum -c SHA256SUMS --quiet` passed |
| Deploy record | `/var/lib/nuxel/p63000-deploy.json` |
| Provider | `gnome-keyring-48.0-3.fc43.aarch64`, UID 0 on `/run/nuxel-wayland/bus` |
| Keyring initialized by agent | **no** |

Post-reboot live checks (recorded):

```
nuxel-wayland active
nuxel-http-bridge active
nuxel-web active
org.freedesktop.secrets owner UID=0
Vault API status: {"success":true,"state":"not_initialized",...}
Vault UI: "Create your Nuxel Vault keyring"
Authenticator UI: "Unlock vault" + "Nuxel Keyring is not initialized. Open Nuxel Vault to create it."
```

## 3. Deployable artifact

The source and deployable archive are generated from the same tree:

```text
release/pwnage63000/nuxel-pwnage63000.tar.gz
release/pwnage63000/nuxel-pwnage63000.tar.gz.sha256

The SHA-256 is published in the adjacent `nuxel-pwnage63000.tar.gz.sha256`
file. Verify it with:

```sh
sha256sum -c release/pwnage63000/nuxel-pwnage63000.tar.gz.sha256
```


Install/use:

```sh
sha256sum -c nuxel-pwnage63000.tar.gz.sha256
tar -xzf nuxel-pwnage63000.tar.gz -C /x
cd /x/nuxel
SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
  tools/pwnage63000/deploy-pwnage63000.sh root@10.20.30.16
```

The archive contains the changed source tree, tests, docs and deploy/rollback
scripts. It does not contain a keyring, a master password, an Authenticator
envelope, a TOTP seed or the per-device launcher secret.

## 4. Rollback

On the handset, as root:

```sh
/usr/lib/nuxel/rollback-pwnage63000.sh \
  /var/backups/nuxel/p63000-20261103T111313Z
```

The rollback:

- verifies the backup manifest first;
- restores the previous Bridge `api.py`/`capabilities.py`, service unit, session
  script, Home app/sw/manifest, registries, Authenticator app and Nuxtore catalog;
- removes only mission-only files that were absent from the backup (Vault app,
  `secret_service.py`, `keyring_api.py`, suspend hook);
- removes the new `nuxel-keyring-lock` hook if it was not in the backup;
- daemon-reloads and restarts `nuxel-http-bridge`/`nuxel-bridge`;
- **preserves** `/root/.local/share/keyrings`, every Secret Service item, the
  Authenticator localStorage envelope and downloaded encrypted archives.

Rollback does **not** remove `gnome-keyring`, `gcr3` or `libsecret` because
removing them would not restore the old Authenticator but could make a keyring
unreadable. If the owner explicitly wants the packages removed and has confirmed
there is no keyring data to retain, use `dnf history undo` for the recorded
transaction; never delete the keyring directory as part of package removal.

## 5. Package decisions

| Package | Action | Reason |
|---|---|---|
| `gnome-keyring` | install/keep | owns `org.freedesktop.secrets`; required for Vault |
| `gcr3` | install/keep | gnome-keyring dependency; ships `gcr-prompter` |
| `libsecret` | install/keep | supported Secret Service client library / `secret-tool` diagnostics |
| Existing Fedora base | unchanged | no kernel/boot/modem/partition writes |
| Repository GPG checks | unchanged/on | package signature policy preserved |

## 6. Safe first-run after deployment

1. Reboot or restart `nuxel-wayland` so Home loads the new registry and the new
   native host.
2. Unlock Home (swipe).
3. Open **Vault** and create the keyring with the owner's master password.
   The agent does not create or guess this credential.
4. Open **Authenticator**, unlock manually with the existing passphrase, then
   opt in to save it in the keyring from **Security**.
5. Verify the existing TOTP accounts/codes before relying on auto-unlock.

## 7. Emergency notes

- If Vault shows “System keyring unavailable”, do not create a fake keyring or
  plaintext file. Check `systemctl status nuxel-http-bridge`,
  `busctl --address=unix:path=/run/nuxel-wayland/bus status org.freedesktop.secrets`,
  and the provider packages.
- If the launcher token path fails, Vault/authenticator fail closed. The native
  host must contain `NUXEL_KEYRING_MINT`; the secret file must be 0600 root and
  64 hex characters; the Bridge must read the same file.
- If a keyring unlock password is lost, there is no recovery. Restore an
  encrypted backup or accept data loss; never attempt to parse/edit the keyring
  file directly.
