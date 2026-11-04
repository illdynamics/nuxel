# PWNAGE-72000 + PWNAGE-73000 — finish-off run — final summary

**Completed:** 2026-11-04T00:13Z (Europe/Amsterdam)
**Repository:** `/x/nuxel`, branch `main`, HEAD `0bed35d8` (unchanged)
**Target:** SM-G975F `beyond2lte`, Fedora 43 aarch64, kernel `4.14.253-gf7194c1d15ed-dirty`
**Boot ID:** `e3b5e426-5c2b-4ac8-ad14-70e2cfb27ab4` — **unchanged; no reboot**
**Concurrent process:** the other CodeSeeq PWNAGE orchestrator was left running;
no worker was launched; no shared orchestrator files were modified.

## Result

| Mission | Result |
|---|---|
| **72000 — finish 62000** | `PARTIAL_IMPLEMENTATION`: deploy-script parity fixed, userspace deployed atomically, source/live hashes match, shell healthy, locked-screen screenshot captured. Physical app/touch matrix and reboot statistics remain owner actions. |
| **73000 — finish 63000** | `IMPLEMENTED_PENDING_OWNER_TEST`: live 63000 hashes match source, all host suites pass, stale P49000 assertion fixed, 63000 artifact rebuilt. Owner must initialize the keyring and run the Vault/Authenticator acceptance. |

**No TWRP and no reflash are required for either mission.** No reboot, flash,
partition write, bootloader change, USB-role change, keyring unlock, or secret
inspection was performed.

## 72000 — what was actually done

- Found the live Home manifest was still the **Nuxel Clipper** manifest
  (`d7a0b744…`) on both live paths, and the live wayland unit was stale
  (`7ea793ab…`).
- Fixed `tools/pwnage62000/deploy-pwnage62000.sh` to stage, back up, atomically
  install and content-assert the canonical Home manifest and wayland unit.
- Fixed `tools/pwnage62000/rollback-pwnage62000.sh` to restore them, and
  installed the updated rollback script on the phone.
- Ran the atomic userspace deployment over strict Wi-Fi SSH: exit 0,
  `DEPLOY_OK`, backup `/var/backups/nuxel/p62000-20261103T231049Z`.
- Live now: Home manifest `f6d0709e…` at both paths, unit `7d00d675…`,
  `FRAMES_OK`, statusbar `ready=true/visible=false/reason=locked`, navdock
  unmapped while locked, all shell units active.
- Captured a real 720×1520 locked-screen screenshot; OCR reads
  “swipe up to unlock”. Evidence: `evidence/screenshots/72000-locked.png`.

## 73000 — what was actually done

- Re-verified all 63000 live file hashes against canonical source: all match.
  No redeploy was needed.
- Re-ran all 63000 host suites: 11 + 14 pytest tests, 39 Node bridge tests,
  32 TOTP vectors, 19 archive tests, 12 password-generator tests, registry
  (42 apps, 0 problems) and Nuxtore verification — all exit 0.
- Repaired the stale `tests/pwnage49000/test_pwnage49000.py` cache assertion;
  10/10 now pass.
- Rebuilt `release/pwnage63000/nuxel-pwnage63000.tar.gz` with the identical
  111-entry file list so it no longer carries the pre-62000 Home manifest.
  New SHA-256 `f794b0f0361e1920f45174cf81c2bd9261e8a9d0b1d375b8b76660102d903c10`;
  `sha256sum -c` passes.
- Live Secret Service is healthy (`org.freedesktop.secrets`, PID 160045, UID 0),
  but `login.keyring` is **absent** — the owner has never initialized it.

## Owner actions (all that remains)

1. Unlock the phone; run the physical Home/lockscreen/GTK/Flatpak/WebKit/touch
   matrix for 72000.
2. Perform owner-approved normal boots/reboots for the 3×/10× timing statistics.
3. Open Vault and create the keyring/master password yourself; then run the
   disposable Vault/Authenticator/TOTP/export/suspend acceptance matrix for
   73000.
4. Optionally install `pytest-check` for the package-manifest suite.

## Evidence index

- `missions/72000/final-report.md`
- `missions/73000/final-report.md`
- `evidence/72000-predeploy-live.txt`
- `evidence/72000-deploy.log`
- `evidence/72000-postdeploy-live.txt`
- `evidence/72000-host-gates.txt`
- `evidence/screenshots/72000-locked.png`
- `evidence/73000-live-parity.txt`
- `evidence/73000-host-gates.txt`
- `evidence/73000-rebuilt-artifact.sha256`
- `evidence/artifacts/nuxel-pwnage63000-pre73000.tar.gz` (preserved old artifact)
- `baseline/`, `run-manifest.json`

## Rollback

```sh
/usr/lib/nuxel/rollback-pwnage62000.sh /var/backups/nuxel/p62000-20261103T231049Z
/usr/lib/nuxel/rollback-pwnage63000.sh /var/backups/nuxel/p63000-20261103T113054Z
```

Both are available but were **not executed live**; doing so would undo the
verified deployment. The 62000 rollback script was exercised by the 22/22
offline rollback/reboot scenarios.
