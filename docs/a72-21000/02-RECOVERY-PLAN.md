# NUXEL A72 / 21000 — 02-RECOVERY-PLAN

## Transport
USB CDC-ACM Live Console `/dev/cu.usbmodem101` (VID 0x18d1 PID 0x4ee7, serial
NUXEL-S10PLUS-0001). Reachability verified before every change via
`nuxel-live.sh --run 'uname -a'`. adb is NOT the recovery channel.

## Known-good snapshot (on phone)
`/var/lib/nuxel/a72-backup-20261025T152149Z/` (symlinked as `a72-backup-latest`)
contains the pre-change copies of the 9 PWA files + `rpm-qa-baseline.txt`, with
`MANIFEST.sha256`. Recorded device hashes (status-bar.js 77f0474f…,
home-settings.js 6b7605f7…) match the protected AHEAD-of-repo baseline.

## Restore (PWA files, from USB console)
```sh
BK=/var/lib/nuxel/a72-backup-latest
cp -a "$BK"/status-bar.js      /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js
cp -a "$BK"/home-settings.js   /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js
cp -a "$BK"/lockscreen.js      /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js
cp -a "$BK"/lockscreen-indicators.js /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js
cp -a "$BK"/app.js             /usr/share/nuxel/pwa/nuxel-home/js/app.js
cp -a "$BK"/navigation.js      /usr/share/nuxel/pwa/nuxel-home/js/navigation.js
cp -a "$BK"/style.css          /usr/share/nuxel/pwa/nuxel-home/css/style.css
cp -a "$BK"/lockscreen.css     /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css
cp -a "$BK"/status-bar.css     /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd
```

## Restore (dnf5 bootstrap, if package transaction must be undone)
```sh
rpm -e dnf5 libdnf5-cli libdnf5 libsolv librepo libmodulemd fmt sdbus-cpp \
       libyaml zchunk-libs systemd-standalone-sysusers coreutils-single \
       glibc-minimal-langpack
```
(recorded in package-install-manifest.csv; `rpm -e` order reverse of install)

## Approval boundaries (owner approval required BEFORE each)
1. Any `rpm -U`/`rpm -e` package transaction (incl. dnf5 bootstrap).
2. Any reboot / service restart that risks the live console or shell.
3. Any firmware blob deployment (audio DSP, BT HCD, SSP) — not attempted without
   licensed/provenanced owner-supplied files.
4. Any USB host/role switch that could sever the only recovery console.
5. RF behavior changes (Bluetooth rfkill unblock / scan).

## What is ALWAYS safe (no approval)
Read-only diagnostics, repo-side code edits, metadata resolution, versioned
backups, and re-running `nuxel-live.sh --run` checks.
