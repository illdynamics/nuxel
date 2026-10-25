# NUXEL A69 — LIVE (phone) vs REPO (working tree) reconciliation

Commit on repo `main`: `37bc270` (merge a65-hyperfix-14000). Working tree has
uncommitted WIP (lockscreen-indicators task) that was **preserved**, not reset.

## PWA files deployed this mission (after patch)
| File | Local sha256 (repo) | Phone sha256 | Match |
|---|---|---|---|
| pwa/nuxel-home/css/style.css | acfb751e…cb5 | acfb751e…cb5 | yes |
| pwa/nuxel-home/js/app.js | ed800ef0…ee4 | ed800ef0…ee4 | yes |
| pwa/nuxel-home/js/lockscreen.js | 5482ae6d…839c3 | 5482ae6d…839c3 | yes |
| pwa/nuxel-home/js/navigation.js | 87098908…4d7 (unchanged) | 87098908…4d7 | yes |

## Pre-patch deployed hashes (backed up to /var/lib/nuxel/a69-backup/)
- style.css 34d68e5891b4d1bf572e213370de4e7944811425b393f0afc1b2526df947ac3c
- app.js 7f86618ff3602b8f380eb2290f5ea5aa5040ff87254c8249223d57da71c28576
- lockscreen.js 1c740ead3719e48aede19937c6b7491c7dad2ca2fe063b1170aa58311fc22b8e

## Native binaries (phone, unchanged this mission)
- /usr/lib/nuxel/nuxel-pwa-host 0fb7d05b…
- /usr/lib/nuxel/nuxel-navdock ffe12854…
- /usr/lib/nuxel/nuxel-button-manager 72d7244e…

## Key live-state facts (not from repo)
- Phone reboots cleanly; journald persists boot logs (`journalctl --list-boots`).
- Button manager can trigger a real `systemctl reboot` from its power menu
  (observed 19:48:52 reboot, source=key — physical, not agent-initiated).
- `nuxel-pwa-host` purges service-worker/WebKit caches on launch, so redeployed
  PWA JS/CSS is picked up on the next reload without a manual cache bump.
