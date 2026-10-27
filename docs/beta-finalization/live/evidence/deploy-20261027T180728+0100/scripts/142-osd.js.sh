#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/osd.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/osd.js
# previous-hash: 7c658be63ae365cc4bcf84d9b3975d14108fae5ce37a3c5cca120ceb49c427b6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/js/osd.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/osd.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/osd.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/osd.js /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/osd.js /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-staged
printf '%s  %s\n' 7c658be63ae365cc4bcf84d9b3975d14108fae5ce37a3c5cca120ceb49c427b6 /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/osd.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/osd.js | grep -q 7c658be63ae365cc4bcf84d9b3975d14108fae5ce37a3c5cca120ceb49c427b6
echo INSTALL-OK
