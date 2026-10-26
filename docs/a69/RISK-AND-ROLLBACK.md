# NUXEL A69 — RISK & ROLLBACK

## What was changed on the phone
Only three launcher PWA files under `/usr/share/nuxel/pwa/nuxel-home/`:
`css/style.css`, `js/app.js`, `js/lockscreen.js`. **No kernel, firmware, boot
chain, partition, package install, or service unit was modified.** No reboot was
initiated by the agent.

## Backup (on phone)
`/var/lib/nuxel/a69-backup/{style.css,app.js,lockscreen.js}` — pre-patch copies
with sha256 recorded in LIVE-VS-REPO.md.

## Rollback (tested restore path)
From the USB Live Console:
```sh
cp -a /var/lib/nuxel/a69-backup/style.css /usr/share/nuxel/pwa/nuxel-home/css/style.css
cp -a /var/lib/nuxel/a69-backup/app.js    /usr/share/nuxel/pwa/nuxel-home/js/app.js
cp -a /var/lib/nuxel/a69-backup/lockscreen.js /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd
```
The restore path was validated by confirming the backup sha256 equals the
pre-patch deployed sha256 for each file. A launcher reload is sufficient (the
host purges service-worker caches at launch; code assets are network-first).

## Recovery route
USB CDC-ACM Live Console `/dev/cu.usbmodem*` (VID 0x18d1 PID 0x4ee7). Verified
working before, during, and after the patch (survived a physical 19:49 reboot
that was **not** agent-initiated — it came from the button-manager power menu,
`source=key`). adb is not the recovery channel.

## One deploy owner
This agent is the sole writer. No parallel phone writers were run.

## Safety boundaries honored
- No firmware blobs fetched/installed (audio Madera DSP, SSP/GNSS, BT, NFC firmware all left absent — recorded as blockers).
- No dnf/systemwide upgrade (dnf is absent; no network).
- No kernel/dtb/driver replacement; no boot flash; no modem/APN/AT provisioning.
- Wi-Fi credentials were never read; saved profiles listed by name only.

## 2026-10-25 addition — Maps PWA (three files)
Changed on the phone (low-risk userspace, no kernel/firmware/boot/package):
`/usr/share/nuxel/pwa/nuxel-apps/maps/{index.html,js/maps.js,sw.js}`.

Backup (on phone): `/var/lib/nuxel/a69-backup-maps/` with pre-patch sha256:
- index.html 152d58179152631c4915ca1cc3d85f0beb7208c6b56a3a36b3bae719b9718a4e
- js/maps.js 4190a630e7bf5bd9ee0583f2d4810ffc98a38fd44ab1232d16e82091c5bb4589
- sw.js      d2ec2ba17c6b1b04380511dd0ba332da4c17f01cf4aa292b56eef0445b782f54

Rollback (USB Live Console):
```sh
cp -a /var/lib/nuxel/a69-backup-maps/index.html /usr/share/nuxel/pwa/nuxel-apps/maps/index.html
cp -a /var/lib/nuxel/a69-backup-maps/maps.js    /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js
cp -a /var/lib/nuxel/a69-backup-maps/sw.js      /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd
```
Post-deploy verification (measured): device sha256 readback == repo sha256 for
all three files; HTTP endpoint serves the new `osm-preset` content; launcher
reloaded with `NAVOWNER native-dock=present` and `STATUSBAR_OVERLAP_CHECK
cells=2 overlaps=none` intact.
