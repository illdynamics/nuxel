#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/home-settings.js
# previous-hash: ab3ccd445e8dba89f8bc1b8e6482362422fe9a95538ef570b38c166a5410686a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-staged
printf '%s  %s\n' ab3ccd445e8dba89f8bc1b8e6482362422fe9a95538ef570b38c166a5410686a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js | grep -q ab3ccd445e8dba89f8bc1b8e6482362422fe9a95538ef570b38c166a5410686a
echo INSTALL-OK
