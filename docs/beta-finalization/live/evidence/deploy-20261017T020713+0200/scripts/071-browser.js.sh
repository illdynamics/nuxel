#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/browser/js/browser.js
# previous-hash: 73367c02bf1af73d42b01a2c2c0645985fe1b600d943f4592cf05774fda95634
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js.nuxel-staged
printf '%s  %s\n' 73367c02bf1af73d42b01a2c2c0645985fe1b600d943f4592cf05774fda95634 /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/browser/js/browser.js | grep -q 73367c02bf1af73d42b01a2c2c0645985fe1b600d943f4592cf05774fda95634
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
