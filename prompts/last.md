/bin/bash -lc "cd /x/nuxel && cd services/nuxel-bridge/src && python3 -c \"                                                                                                                                                                                                                                                                                        21:26 [109/91064]
import importlib.util, sys                                         
for m in ['pwa_store','mail_client']:                                                                                                  
    spec = importlib.util.spec_from_file_location(m, m+'.py')                                
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print(m, 'import ok')                                                                                      
\"" in /x/nuxel                                                                                                                                                                           
 succeeded in 0ms:                                                 
pwa_store import ok                                                
mail_client import ok                                              
                                                                                             
exec                                                               
/bin/bash -lc "cd /x/nuxel/services/nuxel-bridge/src && timeout 20 python3 -c \"import api; print('api import ok')\" 2>&1 | tail -20; echo \"rc="'$?"' in /x/nuxel                        
 succeeded in 0ms:                                                                           
Traceback (most recent call last):                                 
  File "<string>", line 1, in <module>                       
  File "/x/nuxel/services/nuxel-bridge/src/api.py", line 24, in <module>                            
    import dbus                                                                                                                                                                                                                                                                                                                                                             
ModuleNotFoundError: No module named 'dbus'                                                  
rc=0       
                                                                                                                                                                                                                                                                                                                                                                                    exec                                                  
/bin/bash -lc "cd /x/nuxel && echo \"=== HEAD ===\" && git rev-parse HEAD && git branch --show-current && echo \"=== changed file count ===\" && git status --short | grep -v '"'^??'"' | wc -l && echo \"=== untracked (excluding pre-existing prompt files) ===\" && git status --short | grep '"'^??'"' | grep -vE 'TRI-LINK-QUICKSTART.md|full-pwnage-30000.md|pwnage-30000.md' 
| sort" in /x/nuxel                                                
 succeeded in 0ms:                                                                                                                     
=== HEAD ===                                                                                                                           
e12050bc2355386c0b9dadcec51eed3c88ff737c                                                                                                                                                  
nuxel/v0.7.0-numid-audio                                                                                                                                                                  
=== changed file count ===                                         
35                                                                                           
=== untracked (excluding pre-existing prompt files) ===                                                                                                                                                                            
?? docs/beta-finalization/live/evidence/deploy-20261027T211920+0100/
?? docs/beta-finalization/live/evidence/pwnage-30000-hashes.json   
?? pwa/nuxel-apps/photos/tools/                                                                                                                                                                                                                                                                                                                                                     ?? pwa/nuxel-apps/recorder/js/recorder-wav.js                      
?? pwa/nuxel-apps/recorder/tests/                                                            
?? pwa/nuxel-apps/settings/theme-settings.js
?? pwa/nuxel-common/haptics.js                                                                                                                                                                                                                                                                                                                                              
?? pwa/nuxel-common/theme.css                                                                                                          
?? pwa/nuxel-common/theme.js                                                                                                                                                                                                                                                                                                                          
?? pwa/nuxel-home/css/widgets.css                                                                                                      
?? pwa/nuxel-home/js/widgets.js                                                                                                        
?? pwa/nuxel-home/tests/                                           
?? services/nuxel-bridge/src/mail_client.py                                                  
?? services/nuxel-bridge/src/pwa_store.py
?? tests/pwnage30000/                                                                        
?? tools/beta/live/nuxel-30000-pwnage-manifest.json                
                                                                                                                                                                                                                                                                                                                                                      
  ✓ Baseline: inspect architecture, run baseline tests, capture evidence                                                                                                                  
  ✓ Shared foundation: fix bridge persistence backend, theme tokens, haptics path                                    
  ✓ Core productivity apps: Calendar, Clock, Contacts, Files, Notes with tests
  ✓ Widget framework + Notes widget + desktop-2 test                                         
  ✓ Media/hardware apps: Gallery (rename Photos), Recorder, microphone diagnostics           
  ✓ Network apps: Mail config/transport, Weather online, Messages/Phone honest shells                                                                                                     
  ✓ Visual integration: Nuxel Grove + Test Theme, Nuxtore polish                                                                                                                          
  ✓ Regression, package/live-userspace payload + hashes, deployment manifest validation, completion report                      
codex                                                                                                                                                                                     
# PWNAGE-30000 — Completion Report                                                                                                     
                                                                                                                                                                                          
**Git state:** branch `nuxel/v0.7.0-numid-audio`, HEAD `e12050bc2355386c0b9dadcec51eed3c88ff737c`. No `git reset`, no force-push, no destructive clean. Pre-existing untracked prompt files left untouched.                                                                                                                                                                         
                                                                                                                                                                                          
## Environment truth                                                                                                                   
This checkout is the **x86_64 Fedora dev host**, not the S10+. Confirmed: no `/sys/class/timed_output/vibrator`, no `/run/nuxel-haptics`, no `/dev/video*` camera path usable for capture, and `python3` here lacks `dbus`. Therefore **no physical hardware verification was possible**; software paths were implemented and tested offline, and every hardware claim is explicitly
 separated below.                                                                                                                                                                         

## Root causes discovered (and fixed)                              
- **Calendar/Notes/Files/Mail persistence failures:** `api.py` routed `storage.*`, `caldav.*`, `mail.*` to D-Bus methods (`CaldavList`, `StorageListDir`, `MailImapList`, …) that **do not exist** on `org.nuxel.Bridge`. Every save/read fell back to webview `localStorage` (not durable across launcher rebuilds). Fixed by adding an in-process, file-backed store.             
- **Clock tabs "unclickable":** the tab buttons had no click handler — only CSS. Added real tab switching.                                                                                
- **Contacts "Could not open":** native exec path resolved only through a fallback registry lookup and produced a generic failure. Added the three core native apps to the bridge's fixed launch allowlist, plus a precise `native_binary_missing` diagnostic surfaced by the launcher.                                                                                             
- **Weather:** was deliberately offline with no provider. Replaced with live Open-Meteo geocoding + forecast.                                                                             
- **Files:** modal/lifecycle and listing logic were broken; replaced with a single-dialog file browser using the new storage backend.                                                     
- **No shared theme/haptics/widget layer existed.**                                                                                    
                                                                                                                                                                                          
## What was implemented (software)                                                                                                                                                        
                                                                                                                                                                                                                                                                                                                                                                                    ### Shared foundation            
- New `services/nuxel-bridge/src/pwa_store.py`: atomic file-backed storage for calendar, notes/keys, contacts, a traversal-safe file manager (mkdir/rename/delete/copy/move/archive/write-file/read-file), and a haptics FIFO writer. `NUXEL_APP_DATA_DIR`-testable.                                                                                  
- New `services/nuxel-bridge/src/mail_client.py`: IMAP/SMTP (TLS-only) connection test, autodiscovery for Gmail/Microsoft, account config (passwords never stored/logged).
- `api.py`: routes `storage/caldav/contacts/haptics/mail` in-process; precise native-launch errors; native allowlist.                                                                     
- New shared clients: `pwa/nuxel-common/theme.js`, `theme.css`, `haptics.js`.               
                                                                                                                                                                                          
### Apps                                                                                                                               
- **Calendar:** durable save/delete, validation, all-day/location/reminder fields, duplicate-save lock, edit/delete, platform date/time pickers (no legacy keyboard path).
- **Clock:** tab switching; timer/stopwatch/alarm lifecycle already present and retained; added alarm vibration setting + bridge-persisted alarms + haptics on ring.                      
- **Contacts/Phone/Messages:** launch path fixed/honest; native apps already had honest capability labels and no fake calls/SMS.                                                          
- **Files:** full browser (breadcrumbs, select, CRUD, copy/cut/paste, ZIP create/extract, upload via write-file, traversal/symlink protection).
- **Notes:** durable autosave + explicit save with dirty/saved/error state; search/pin/export retained.                                                                                   
- **Mail:** account config mirrored to bridge; autodiscover + staged connection test; transport remains honestly `NEEDS_CREDENTIALS` for fetch/send without runtime credentials.
- **Weather:** live Open-Meteo, automatic-location toggle, manual city lookup (Eindhoven verified against the real API), stale-cache/offline states, C/F.
- **Gallery:** Photos renamed to “Gallery”; sample-image seeding tool (`photos/tools/seed-samples.py`) writes real PNGs through the media store and was verified to thumbnail.
- **Recorder:** one-tap UI, mic probe/diagnostics, save-location setting, real 16-bit PCM WAV encoder (`recorder-wav.js`).                                                                
- **Nuxtore:** themed to the shared token system; the existing verification-gated local catalog was left honest (no fake installs).                                                       
- **Widgets:** `widgets.js` registry + per-desktop persistence + Notes widget + Home Settings flow; secondary-desktop behavior covered by an automated test (see below).                  

### Theme        
- **Nuxel Grove** (green, default) and **Test Theme** (orange) in `theme.css`, applied immediately via `data-theme` + same-origin `storage` propagation, with a Settings Appearance page.
                                                                                                                                       
## Tests executed — real results                                                                                                                                                                                                                                                                                                                                            
- `python3 -m pytest tests/ -q` → **77 passed** (56 baseline + 13 new store + 8 new mail).
- `python3 tools/s10plus/a33/tests/test-core-apps.py --no-runtime` → **86 PASS / 0 FAIL**.   
- New JS tests: `test-widgets.js`, `test-theme-haptics.js`, `test-recorder-wav.js` → all pass (auto-discovered by `U-apps-js`).                                                                                                                                                                                                                                                     - `U-apps-js`, `U-pwa-bridge`, `U-bridge-activation`, `U-pwa-wiring`, `U-services-portal`, `U-services-notifications`, all `L1-*` → **PASS**.
- Offline-safe live-tool tests (`test_tri_link.py`, `test_owner_capture.py`, `test_live_reload_and_transport.py`, `test_live_lib.py`) → **134 passed**.
- Full `tools/beta/run-all-tests.sh` → **gate RED, 52 suites: 33 pass / 7 fail / 5 warn / 3 skip / 4 external**. The 7 hard failures are **pre-existing other-group/infrastructure failures** (missing `tools/s10plus/a33/nuxelctl`, non-executable `services/nuxel-web/bin/nuxel-web`, aarch64 artefact gates, boot/animation/touch groups) — none belong to the changed app suites
; my suites all pass.                                                                                                                  
- `python3 -m pytest tools/beta/live/tests -q` (spec command) → 187 tests collect; the full run **blocks on live-device/console tests**, so a bounded offline subset was run instead (134 pass).                                                                                                                                                                                    
                                                                                                                                                                                          
## Packaging / deployment validation                                                                                                                                                      
- New delta manifest: `tools/beta/live/nuxel-30000-pwnage-manifest.json` (43 runtime files). 
- Dry-run validation: `python3 tools/beta/live/nuxel-live-deploy.py --manifest … --json` → **violations: [], 43 steps planned, verdict IMPLEMENTED_NOT_DEPLOYED** (no `--apply`, correct).
- SHA-256 hash manifest: `docs/beta-finalization/live/evidence/pwnage-30000-hashes.json` (43 files, 431,051 bytes).                                                                       
- `tools/verify-pwa-assets.sh --quiet` → **OK**.                                             

## Live-device verification
**Not performed — no verified target was connected.** No live userspace was deployed. The following remain outstanding as physical acceptance tests:
- vibration motor feel, keyboard keypress haptics;
- real microphone capture/playback and WAV file on device;
- Gallery sample images on the device Pictures/media store;
- real IMAP/SMTP against a provider (requires owner-supplied credentials/authorization);
- Contacts native binary present/launch on device;
- Notes widget visible on physical **desktop 2** (automated desktop-2 isolation test passes; physical check pending).

## Blocked / FAIL
- **BLOCKED:** all hardware verification (above) — no device.
- **BLOCKED:** Mail real send/receive with live credentials (no credentials and no test server run).
- **Pre-existing FAIL (not introduced):** full offline gate red from other build groups (`U-regression-guard-selftest`, `U-baseline-regression-guard`, `U-baseline-a32-suite`, `U-boot-a33-suite`, `U-p3-a33-suite`, `U-userspace-a33-suite`, `U-security-firewall`) and the launcher-vs-canonical registry drift reported by `verify-app-registry.py`.

## Rollback
No commit/release/tag was created and nothing was deployed. All edits are working-tree changes. Rollback is `git checkout -- <file>` for modified files and removing the listed new files; the deploy manifest is a new additive file and the CI step is a single new workflow step. For the (not-run) live deploy, the manifest declares `restore <target>.nuxel-rollback` + `systemctl restart nuxel-web` / `nuxel-http-bridge.service`.

## Known limitations / next steps
1. Run a real S10+ owner test for haptics, mic/WAV, Gallery samples, and the desktop-2 Notes widget.
2. Obtain owner-authorized credentials (or a controlled mail server) to exercise real IMAP/SMTP end-to-end.
3. Reconcile the pre-existing launcher apps.js ↔ canonical registry drift and the missing `nuxelctl`/`nuxel-web` executable permissions so the full offline gate can go green.
4. Consider adding `tests/pwnage30000` to the canonical `run-all-tests.sh` registry (currently covered by the sanctioned `python3 -m pytest tests/` command and the new CI step).
# PWNAGE-30000 — Completion Report

**Git state:** branch `nuxel/v0.7.0-numid-audio`, HEAD `e12050bc2355386c0b9dadcec51eed3c88ff737c`. No `git reset`, no force-push, no destructive clean. Pre-existing untracked prompt files left untouched.

## Environment truth
This checkout is the **x86_64 Fedora dev host**, not the S10+. Confirmed: no `/sys/class/timed_output/vibrator`, no `/run/nuxel-haptics`, no `/dev/video*` camera path usable for capture, and `python3` here lacks `dbus`. Therefore **no physical hardware verification was possible**; software paths were implemented and tested offline, and every hardware claim is explicitly separated below.

## Root causes discovered (and fixed)
- **Calendar/Notes/Files/Mail persistence failures:** `api.py` routed `storage.*`, `caldav.*`, `mail.*` to D-Bus methods (`CaldavList`, `StorageListDir`, `MailImapList`, …) that **do not exist** on `org.nuxel.Bridge`. Every save/read fell back to webview `localStorage` (not durable across launcher rebuilds). Fixed by adding an in-process, file-backed store.
- **Clock tabs "unclickable":** the tab buttons had no click handler — only CSS. Added real tab switching.
- **Contacts "Could not open":** native exec path resolved only through a fallback registry lookup and produced a generic failure. Added the three core native apps to the bridge's fixed launch allowlist, plus a precise `native_binary_missing` diagnostic surfaced by the launcher.
- **Weather:** was deliberately offline with no provider. Replaced with live Open-Meteo geocoding + forecast.
- **Files:** modal/lifecycle and listing logic were broken; replaced with a single-dialog file browser using the new storage backend.
- **No shared theme/haptics/widget layer existed.**

## What was implemented (software)

### Shared foundation
- New `services/nuxel-bridge/src/pwa_store.py`: atomic file-backed storage for calendar, notes/keys, contacts, a traversal-safe file manager (mkdir/rename/delete/copy/move/archive/write-file/read-file), and a haptics FIFO writer. `NUXEL_APP_DATA_DIR`-testable.
- New `services/nuxel-bridge/src/mail_client.py`: IMAP/SMTP (TLS-only) connection test, autodiscovery for Gmail/Microsoft, account config (passwords never stored/logged).
- `api.py`: routes `storage/caldav/contacts/haptics/mail` in-process; precise native-launch errors; native allowlist.
- New shared clients: `pwa/nuxel-common/theme.js`, `theme.css`, `haptics.js`.

### Apps
- **Calendar:** durable save/delete, validation, all-day/location/reminder fields, duplicate-save lock, edit/delete, platform date/time pickers (no legacy keyboard path).
- **Clock:** tab switching; timer/stopwatch/alarm lifecycle already present and retained; added alarm vibration setting + bridge-persisted alarms + haptics on ring.
- **Contacts/Phone/Messages:** launch path fixed/honest; native apps already had honest capability labels and no fake calls/SMS.
- **Files:** full browser (breadcrumbs, select, CRUD, copy/cut/paste, ZIP create/extract, upload via write-file, traversal/symlink protection).
- **Notes:** durable autosave + explicit save with dirty/saved/error state; search/pin/export retained.
- **Mail:** account config mirrored to bridge; autodiscover + staged connection test; transport remains honestly `NEEDS_CREDENTIALS` for fetch/send without runtime credentials.
- **Weather:** live Open-Meteo, automatic-location toggle, manual city lookup (Eindhoven verified against the real API), stale-cache/offline states, C/F.
- **Gallery:** Photos renamed to “Gallery”; sample-image seeding tool (`photos/tools/seed-samples.py`) writes real PNGs through the media store and was verified to thumbnail.
- **Recorder:** one-tap UI, mic probe/diagnostics, save-location setting, real 16-bit PCM WAV encoder (`recorder-wav.js`).
- **Nuxtore:** themed to the shared token system; the existing verification-gated local catalog was left honest (no fake installs).
- **Widgets:** `widgets.js` registry + per-desktop persistence + Notes widget + Home Settings flow; secondary-desktop behavior covered by an automated test (see below).

### Theme
- **Nuxel Grove** (green, default) and **Test Theme** (orange) in `theme.css`, applied immediately via `data-theme` + same-origin `storage` propagation, with a Settings Appearance page.

## Tests executed — real results
- `python3 -m pytest tests/ -q` → **77 passed** (56 baseline + 13 new store + 8 new mail).
- `python3 tools/s10plus/a33/tests/test-core-apps.py --no-runtime` → **86 PASS / 0 FAIL**.
- New JS tests: `test-widgets.js`, `test-theme-haptics.js`, `test-recorder-wav.js` → all pass (auto-discovered by `U-apps-js`).
- `U-apps-js`, `U-pwa-bridge`, `U-bridge-activation`, `U-pwa-wiring`, `U-services-portal`, `U-services-notifications`, all `L1-*` → **PASS**.
- Offline-safe live-tool tests (`test_tri_link.py`, `test_owner_capture.py`, `test_live_reload_and_transport.py`, `test_live_lib.py`) → **134 passed**.
- Full `tools/beta/run-all-tests.sh` → **gate RED, 52 suites: 33 pass / 7 fail / 5 warn / 3 skip / 4 external**. The 7 hard failures are **pre-existing other-group/infrastructure failures** (missing `tools/s10plus/a33/nuxelctl`, non-executable `services/nuxel-web/bin/nuxel-web`, aarch64 artefact gates, boot/animation/touch groups) — none belong to the changed app suites; my suites all pass.
- `python3 -m pytest tools/beta/live/tests -q` (spec command) → 187 tests collect; the full run **blocks on live-device/console tests**, so a bounded offline subset was run instead (134 pass).

## Packaging / deployment validation
- New delta manifest: `tools/beta/live/nuxel-30000-pwnage-manifest.json` (43 runtime files).
- Dry-run validation: `python3 tools/beta/live/nuxel-live-deploy.py --manifest … --json` → **violations: [], 43 steps planned, verdict IMPLEMENTED_NOT_DEPLOYED** (no `--apply`, correct).
- SHA-256 hash manifest: `docs/beta-finalization/live/evidence/pwnage-30000-hashes.json` (43 files, 431,051 bytes).
- `tools/verify-pwa-assets.sh --quiet` → **OK**.
- CI: added a PWNAGE-30000 regression step to `.github/workflows/release.yml` (validated as YAML).

## Live-device verification
**Not performed — no verified target was connected.** No live userspace was deployed. The following remain outstanding as physical acceptance tests:
- vibration motor feel, keyboard keypress haptics;
- real microphone capture/playback and WAV file on device;
- Gallery sample images on the device Pictures/media store;
- real IMAP/SMTP against a provider (requires owner-supplied credentials/authorization);
- Contacts native binary present/launch on device;
- Notes widget visible on physical **desktop 2** (automated desktop-2 isolation test passes; physical check pending).

## Blocked / FAIL
- **BLOCKED:** all hardware verification (above) — no device.
- **BLOCKED:** Mail real send/receive with live credentials (no credentials and no test server run).
- **Pre-existing FAIL (not introduced):** full offline gate red from other build groups (`U-regression-guard-selftest`, `U-baseline-regression-guard`, `U-baseline-a32-suite`, `U-boot-a33-suite`, `U-p3-a33-suite`, `U-userspace-a33-suite`, `U-security-firewall`) and the launcher-vs-canonical registry drift reported by `verify-app-registry.py`.

## Rollback
No commit/release/tag was created and nothing was deployed. All edits are working-tree changes. Rollback is `git checkout -- <file>` for modified files and removing the listed new files; the deploy manifest is a new additive file and the CI step is a single new workflow step. For the (not-run) live deploy, the manifest declares `restore <target>.nuxel-rollback` + `systemctl restart nuxel-web` / `nuxel-http-bridge.service`.

## Known limitations / next steps
1. Run a real S10+ owner test for haptics, mic/WAV, Gallery samples, and the desktop-2 Notes widget.
2. Obtain owner-authorized credentials (or a controlled mail server) to exercise real IMAP/SMTP end-to-end.
3. Reconcile the pre-existing launcher apps.js ↔ canonical registry drift and the missing `nuxelctl`/`nuxel-web` executable permissions so the full offline gate can go green.
4. Consider adding `tests/pwnage30000` to the canonical `run-all-tests.sh` registry (currently covered by the sanctioned `python3 -m pytest tests/` command and the new CI step).
tokens used
41,227,367
[codeseeq] stopping owned bridge process (pid=2276316)
wicked@dextronux:/x/nuxel$ cspt "ok now write the last version to the phone as well
> ^C
wicked@dextronux:/x/nuxel$ vim last.md
wicked@dextronux:/x/nuxel$ 

