#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/settings-store.js
# previous-hash: 383e068515aba43da0026d6dc1e0250f34cd87f8f1d7014db2c7831cd18c9c1d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-staged
printf '%s  %s\n' 383e068515aba43da0026d6dc1e0250f34cd87f8f1d7014db2c7831cd18c9c1d /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js | grep -q 383e068515aba43da0026d6dc1e0250f34cd87f8f1d7014db2c7831cd18c9c1d
echo INSTALL-OK
