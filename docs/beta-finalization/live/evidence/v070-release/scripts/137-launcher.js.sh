#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/launcher.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/launcher.js
# previous-hash: 2171f661c354a46cf1f11f515b333f7171f7f3c41c2bc29950c294dfc3fef91b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/launcher.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/launcher.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/launcher.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/launcher.js /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/launcher.js /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged
printf '%s  %s\n' 2171f661c354a46cf1f11f515b333f7171f7f3c41c2bc29950c294dfc3fef91b /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/launcher.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/launcher.js | grep -q 2171f661c354a46cf1f11f515b333f7171f7f3c41c2bc29950c294dfc3fef91b
echo INSTALL-OK
