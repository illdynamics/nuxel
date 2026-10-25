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
