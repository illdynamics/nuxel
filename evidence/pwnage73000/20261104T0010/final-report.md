# PWNAGE-73000 — Finish/prove PWNAGE-63000 — final report

**Date:** 2026-11-04 (Europe/Amsterdam) / 2026-11-03T23:11Z UTC
**Repository:** `/x/nuxel`, branch `main`, HEAD `0bed35d881ba674a21f67d31501e84f1031992b5`
**Target:** `root@10.20.30.16`, SM-G975F `beyond2lte`, Fedora 43 aarch64
**Kernel:** `4.14.253-gf7194c1d15ed-dirty`
**Boot ID:** `e3b5e426-5c2b-4ac8-ad14-70e2cfb27ab4` (unchanged; no reboot)
**Dirty owner tree:** 154 entries preserved; no reset/clean/stash/commit/push.

## Executive result

PWNAGE-63000's installed userspace is consistent with the canonical source and
all 63000 host suites pass. The stale PWNAGE-49000 cache assertion that failed
against the current `v63000-pw63001` tree was repaired, and the 63000 release
artifact was rebuilt because it still carried the pre-62000 Home manifest.

The remaining 63000 work is owner-only: the live keyring has **never been
initialized** (`/root/.local/share/keyrings/login.keyring` absent), so Vault
create/unlock/lock/copy/delete, Authenticator linking, TOTP enrollment,
export/import, suspend re-lock and capability isolation could not be physically
exercised without the owner's master password. No secret was read, created,
unlocked, exported or logged.

**Final status: `IMPLEMENTED_PENDING_OWNER_TEST`** (live files `INSTALLED`;
owner initialization and acceptance remain `OWNER_ACTION_REQUIRED`).
**TWRP/reflash: not required.**

## What changed

| File | Change |
|---|---|
| `tests/pwnage49000/test_pwnage49000.py` | Replaced the stale `v62000-pw62000` assertion with the live manifest's `nuxel.cache_version` as source of truth (plus agreement with `sw.js`), and updated the app.js cache-buster to `p62000`. |
| `release/pwnage63000/nuxel-pwnage63000.tar.gz` | Rebuilt from the current tree with the identical 111-entry file list. Old SHA-256 `899fffca24c46ca468ab84976340b1725efdc9735084f198b904fcd248008818`; new SHA-256 `f794b0f0361e1920f45174cf81c2bd9261e8a9d0b1d375b8b76660102d903c10`. The embedded `pwa/nuxel-home/manifest.json` is now `f6d0709e…` (Nuxel Home, registry_version 12), not the stale pre-62000 copy. |
| `release/pwnage63000/nuxel-pwnage63000.tar.gz.sha256` | Updated to the new artifact hash. `sha256sum -c` passes. |

No 63000 source/security logic was changed. No live credential or keyring file
was read or modified.

## Live source parity (all match)

| Live file | SHA-256 |
|---|---|
| `/usr/lib/nuxel/nuxel-bridge/api.py` | `aab569150a9f489b60acfe96c0188702f688e231158dd73ffb8bd7e0ca569479` |
| `/usr/lib/nuxel/nuxel-bridge/capabilities.py` | `09491c673eae7c34d015cb8918d872116da6edff8a6a090f216e9b275b2573d9` |
| `/usr/lib/nuxel/nuxel-bridge/secret_service.py` | `11dfb11a145819a5879749c087465880814130ee047dfec6f17e6b02486c6a56` |
| `/usr/lib/nuxel/nuxel-bridge/keyring_api.py` | `d3d8aa15f3fa5a34c80b02404ad46ad489dfc16fcea4fa05e84e51ff875fd9f4` |
| `/etc/systemd/system/nuxel-http-bridge.service` | `45a593dd8a2dadbc3330f1025dcb78b541ed2d50042958be03fe342d914e59f5` |
| `/usr/share/nuxel/pwa/nuxel-common/bridge.js` | `ced52672bccd82aaa916360bc13146f0b69b2c5540ddc0337ea6d129132f0048` |
| `/usr/share/nuxel/pwa/nuxel-common/app-registry.json` | `610097c560f40109e13aa105e6cc33a49eeecf974e96c03aefe1b5945da6e739` |
| `/usr/share/nuxel/pwa/nuxel-apps/vault/index.html` | `7cfcfecba2bed4f1aa63c6fd483dca500f11842bfc57a77b3ce0049f58c41294` |
| `/usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html` | `822bdf1c3243c5dc37e354a7ea53d94ec4c65f870649b376082dade301176ad5` |
| `/usr/lib/systemd/system-sleep/nuxel-keyring-lock` | `de0cfe24f73b9e7b1db2d1d0b13dc25cc8a21e78c1e3bde0858be4b0fafd3100` |

Because the live files match and the deploy receipt is valid, no redeploy was
performed: `NO_REDEPLOY_NEEDED`.

## Live Secret Service / keyring state (metadata only)

- Packages: `gnome-keyring-48.0-3.fc43.aarch64`, `gcr3-3.41.1-11.fc43.aarch64`, `libsecret-0.21.8.2-2.fc43.aarch64`.
- `org.freedesktop.secrets` owner: `PID=160045`, `UID=0`, `EUID=0` on `unix:path=/run/nuxel-wayland/bus`.
- `/root/.local/share/keyrings/login.keyring`: **ABSENT** — owner has not initialized the keyring/vault.
- `/etc/nuxel/keyring-launcher.secret`: mode `0600`, owner `root:root`, size 65 bytes; contents not read.
- Durable receipt `/var/lib/nuxel/p63000-deploy.json`: `status=deployed_userspace_and_rebooted`, post-reboot verified `2026-11-03T11:37:06Z`, backup `/var/backups/nuxel/p63000-20261103T113054Z`.
- `nuxel-wayland`, `nuxel-http-bridge`, `nuxel-bridge`, `nuxel-web`: active.

## Host test results

Full output: `evidence/73000-host-gates.txt`.

| Command | Exit | Result |
|---|---:|---|
| `python3 -m pytest -q tests/pwnage63000/test_secret_service.py` | 0 | 11 passed |
| `python3 -m pytest -q tests/pwnage63000/test_vault_app.py` | 0 | 14 passed |
| `node --test tests/pwnage63000/test_bridge_keyring.mjs` | 0 | 39 passed, 0 failed |
| `node pwa/nuxel-apps/authenticator/tests/test-vault.js` | 0 | all PASS |
| `node pwa/nuxel-apps/authenticator/tests/test-totp-vectors.js` | 0 | 32 passed, 0 failed |
| `node pwa/nuxel-apps/vault/tests/test-archive.js` | 0 | 19 passed, 0 failed |
| `node pwa/nuxel-apps/vault/tests/test-pwgen.js` | 0 | 12 passed, 0 failed |
| `python3 tools/s10plus/a33/verify-app-registry.py` | 0 | apps=42 problems=0 warnings=0 deferred=1 `OFFLINE_TESTED_WITH_DEFERRALS` |
| `python3 pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py` | 0 | all packages verified |
| `python3 -m pytest -q tests/pwnage49000/test_pwnage49000.py` | 0 | 10 passed (stale assertion fixed) |
| `sha256sum -c release/pwnage63000/nuxel-pwnage63000.tar.gz.sha256` | 0 | OK |

## Physical acceptance

| Criterion | State |
|---|---|
| Live file parity | `INSTALLED` |
| Secret Service provider running | verified (PID/UID/EUID) |
| Keyring initialization | `OWNER_ACTION_REQUIRED` (no keyring exists) |
| Vault create/edit/copy/delete | `OWNER_ACTION_REQUIRED` |
| Lock/unlock fail-closed | `OWNER_ACTION_REQUIRED` |
| Authenticator link/auto-unlock | `OWNER_ACTION_REQUIRED` |
| TOTP/OATH enrollment | `OWNER_ACTION_REQUIRED` |
| Encrypted export/import | `OWNER_ACTION_REQUIRED` |
| Suspend/screen-lock re-lock | `OWNER_ACTION_REQUIRED` |
| Capability isolation live replay | `OWNER_ACTION_REQUIRED` (host tests pass) |
| Microsoft push/passwordless | `NOT_SUPPORTED` (OATH/TOTP only) |
| No secret leakage | no secret was read/created/logged during this run |
| Rollback preservation | host-tested in 63000; live rollback `NOT_TESTED_LIVE` |
| TWRP/reflash | **not required** |

## Remaining owner actions

1. Unlock Home and open Vault to create the keyring/master password. The agent
   must not see or record it.
2. Run the disposable Vault lifecycle and the locked-read/wrong-password
   fail-closed checks.
3. Link Authenticator with consent, enroll a disposable OATH/TOTP account, and
   verify reset isolation and suspend/screen-lock re-lock.
4. Test encrypted export/import with a disposable passphrase and one permitted
   Entra OATH enrollment if the tenant allows it.
5. Optionally install `pytest-check` for `tools/s10plus/a33/tests/test-packages-manifest.py`; its absence is an environment limitation, not a 63000 logic failure.

## Rollback

```sh
/usr/lib/nuxel/rollback-pwnage63000.sh /var/backups/nuxel/p63000-20261103T113054Z
```

The rollback preserves keyring data, the Authenticator envelope and the launcher
secret. It was not run live after the owner's data state was observed; live
rollback is `NOT_TESTED_LIVE`.
