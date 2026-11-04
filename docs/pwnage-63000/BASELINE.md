# PWNAGE-63000 — Baseline and source-of-truth capture

Captured: 2026-11-03 (Europe/Amsterdam), before source changes were deployed.

## 1. Repository

| Fact | Value |
|---|---|
| Repository root | `/x/nuxel` |
| Branch | `main` |
| HEAD | `0bed35d881ba674a21f67d31501e84f1031992b5` |
| Upstream | `origin/main` at the same commit |
| Version | `v0.7.5-beta` (`VERSION`) |
| Working tree at capture | **108 pre-existing modified paths** (prior PWNAGE work). This mission did not discard or reset them. |
| New mission tree | `pwa/nuxel-apps/vault/`, `services/nuxel-bridge/src/{secret_service,keyring_api}.py`, `tests/pwnage63000/`, `tools/pwnage63000/`, `docs/pwnage-63000/` |

The source archive's confirmed paths all exist. The Authenticator source matched the live handset byte-for-byte at capture:

```
67e8bf5d2678ef491b53769d5037413ef365c8116a26811632bb315df0b59516  authenticator.js
448136cf8ffd06977c1fc5f2d849f40a2b32ee92b9c883dc403562c30eb9675d  vault.js
```

## 2. Live S10+ image

| Fact | Value |
|---|---|
| Target | Samsung Galaxy S10+ `SM-G975F`, `beyond2lte`, Exynos 9820 |
| OS | Fedora Linux 43 (Forty Three), aarch64 |
| Kernel | `4.14.253-gf7194c1d15ed-dirty` |
| Boot | `root=/dev/sda25`, `androidboot.verifiedbootstate=orange`; no boot/kernel/DTB flash performed |
| Session | `phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini -E /usr/lib/nuxel/nuxel-session.sh` |
| Session owner | `root` (the whole graphical session, PWA host and HTTP bridge run as root on this image) |
| Active session script source | `tools/s10plus/a45/nuxel-session.sh` → `/usr/lib/nuxel/nuxel-session.sh` |
| Active compositor unit | `nuxel-wayland.service` |
| PWA host | `/usr/lib/nuxel/nuxel-pwa-host` (root) |
| HTTP bridge | `/usr/bin/nuxel-http-bridge` → `/usr/bin/python3 /usr/lib/nuxel/nuxel-bridge/api.py`, listening `127.0.0.1:8080`, root |
| Static PWA server | `nuxel-web.service`, `127.0.0.1:8000`, docroot `/usr/share/nuxel` |
| App registry | `/etc/nuxel/app-registry/app_registry.json` |

Live/source drift found and recorded (not silently overwritten):

- `api.py` live hash `a337121202eff07c36cfc2f8e45a3043e9110dac8f37f2223174acbca46eb5fd` **matched** the repository at capture.
- `bridge.py` live hash `f9871eee964c35ee9ccbe64d84ed93599ced0b13ce20a2e28d6dc7095b029bae` differed from the repository (`72b8868be…`). This mission deploys the repository version, so the drift is removed.
- `capabilities.py` live and repository hashes matched.
- Authenticator `authenticator.js` and `vault.js` live and repository hashes matched.

## 3. D-Bus and keyring state before implementation

Two session buses exist:

- `/run/nuxel-wayland/bus` — root-owned compositor/PWA/bridge session, used by `nuxel-pwa-host` and the HTTP bridge (`DBUS_SESSION_BUS_ADDRESS` is already set in `nuxel-http-bridge.service`).
- `/run/user/1000/bus` — the `nuxel` user bus used by Flatpak/portals. It is **not** the bus used by the PWA host or HTTP bridge.

At capture:

```
rpm -q gnome-keyring libsecret gcr3
package gnome-keyring is not installed
libsecret-0.21.8.2-2.fc43.aarch64
gcr3-3.41.1-11.fc43.aarch64
```

`secret-tool` was present (from libsecret) but is diagnostic-only. `org.freedesktop.secrets` had **no owner**. There was no `/root/.local/share/keyrings` or `/home/nuxel/.local/share/keyrings`. `images/config/packages.yml` mentioned `gnome-keyring`, but the generated S10+ manifest did **not** contain it; that generic file is not the S10+ source of truth.

During Phase 1 validation, `gnome-keyring-48.0-3.fc43.aarch64` was installed on the handset from Fedora 43 and `org.freedesktop.secrets` was activated on `/run/nuxel-wayland/bus`. This was a deliberate, reversible package transaction; the package is now recorded in the S10+ manifest source.

### Stock prompt finding

GNOME Keyring's D-Bus activation and `gcr-prompter` work, and the internal prompt calls (`BeginPrompting`, `PerformPrompt`) were observed. However, `gcr-prompter` did **not** map a visible toplevel in Phoc: `nuxel-foreign-toplevel list` showed only `nuxel-pwa-host` and Stremio, and a `grim` screenshot taken during the prompt was byte-for-byte identical to the baseline screenshot (0 changed pixels). Therefore the stock Secret Service prompt is not a usable unlock UI on this image.

The implementation uses the provider's supported PAM-compatible path instead: the Vault UI collects the master password and the bridge pipes it to `gnome-keyring-daemon --login --daemonize` on **stdin**. This is the same path `pam_gnome_keyring` uses. It was proven in an isolated bus/HOME before touching the live keyring.

## 4. Authenticator current encrypted envelope

The existing envelope is still at:

```
localStorage key: nuxel-authenticator-envelope-v1
localStorage value length: 654 bytes
```

Only the key name and length were read. The ciphertext and passphrase were not printed, copied or logged. The envelope is an AES-256-GCM payload under PBKDF2-SHA-256 with a 16-byte salt and a fresh 12-byte GCM IV per save, as asserted by `pwa/nuxel-apps/authenticator/tests/test-vault.js`.

## 5. Baseline tests

| Test | Result |
|---|---|
| `node pwa/nuxel-apps/authenticator/tests/test-vault.js` | 39 passed, 0 failed |
| `node pwa/nuxel-apps/authenticator/tests/test-totp-vectors.js` | 32 passed, 0 failed |
| `pytest tests/pwnage49000/test_authenticator_p49000.py` | 6 passed |
| `python3 tools/s10plus/a33/verify-app-registry.py` | **FAILED**: 7 pre-existing drifts (Clipper capabilities/manifest, apps.js registry version 10 vs 11, native-shell Clipper URL) |

The registry failures were repaired as part of this mission (canonical version 12, 42 apps, Clipper metadata, regenerated native shell).

## 6. Package/catalog source of truth

- S10+ essential packages: `tools/s10plus/a33/verify-packages.py` (`ESSENTIAL_GROUPS`), generated into `images/s10plus/packages-manifest.json` by `python3 tools/s10plus/a33/verify-packages.py --emit-manifest`.
- Rootfs builder: `images/s10plus/build-phone-rootfs-inside-fedora.sh`.
- Canonical app registry: `pwa/nuxel-common/app-registry.json`; consumers include `pwa/nuxel-home/js/apps.js`, `shell/nuxel-home-native/nuxel_home/app_registry.json`, `GET /api/v1/apps/registry`, and the installed `/etc/nuxel/app-registry/app_registry.json`.
- Nuxtore: `python3 pwa/nuxel-apps/nuxtore/tools/nuxtore-stage.py` (regenerates bundles and Ed25519 signatures) and `nuxtore-verify.py` (re-hashes and verifies). No hashes were hand-edited.

## 7. Baseline conclusion

- A real Secret Service provider can be made operational on the S10+ session bus.
- The stock gcr prompt is not visible on Phoc; the supported PAM login path is used instead.
- No keyring collection existed, so the owner will create the first Nuxel Vault master password after deployment.
- The existing Authenticator envelope is untouched and remains the migration source.
