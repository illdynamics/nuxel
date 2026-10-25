#!/bin/sh
# NUXEL A72/21000 — reviewed rollback. NEVER reboots/flashes without approval.
set -eu
BK=/var/lib/nuxel/a72-backup-latest

echo "== Restore Maps PWA (deployed this run) =="
cp -a "$BK/maps/index.html" /usr/share/nuxel/pwa/nuxel-apps/maps/index.html
cp -a "$BK/maps/maps.js"    /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js
cp -a "$BK/maps/sw.js"      /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js

echo "== Restore home PWA (if ever touched) =="
cp -a "$BK/status-bar.js"   /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js
cp -a "$BK/home-settings.js" /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js
cp -a "$BK/lockscreen.js"   /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js
cp -a "$BK/lockscreen-indicators.js" /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js
cp -a "$BK/app.js"          /usr/share/nuxel/pwa/nuxel-home/js/app.js
cp -a "$BK/navigation.js"   /usr/share/nuxel/pwa/nuxel-home/js/navigation.js
cp -a "$BK/style.css"       /usr/share/nuxel/pwa/nuxel-home/css/style.css
cp -a "$BK/lockscreen.css"  /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css
cp -a "$BK/status-bar.css"  /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css

echo "== Reload launcher =="
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd

echo "== dnf5 bootstrap undo (only if installed) =="
echo "rpm -e dnf5 libdnf5-cli libdnf5 libsolv librepo libmodulemd fmt sdbus-cpp libyaml zchunk-libs systemd-standalone-sysusers coreutils-single glibc-minimal-langpack"
echo "(uncomment to run; reverse of install order)"
