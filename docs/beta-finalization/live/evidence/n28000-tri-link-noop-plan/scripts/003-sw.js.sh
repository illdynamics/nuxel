#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-home/sw.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/sw.js
# previous-hash: 590158d0740ed5673f84cd9783a0d7664bf2176c692c259b27025df24bb86f2d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T164331-2129532 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T164331-2129532 /usr/share/nuxel/pwa/nuxel-home/sw.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T164331-2129532 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T164331-2129532; fi
test -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged
printf '%s  %s\n' 590158d0740ed5673f84cd9783a0d7664bf2176c692c259b27025df24bb86f2d /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | grep -q 590158d0740ed5673f84cd9783a0d7664bf2176c692c259b27025df24bb86f2d
echo INSTALL-OK
