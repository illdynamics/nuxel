#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/browser/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/browser/index.html
# previous-hash: 824d43a35c7ca1b42b27b273cc7d1e01cc53f5d4512b2f2bad4ce7ac7400f1cd
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/browser/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/browser/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/browser/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/browser/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/index.html /usr/share/nuxel/pwa/nuxel-apps/browser/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/browser/index.html.nuxel-staged
printf '%s  %s\n' 824d43a35c7ca1b42b27b273cc7d1e01cc53f5d4512b2f2bad4ce7ac7400f1cd /usr/share/nuxel/pwa/nuxel-apps/browser/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/browser/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/browser/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/browser/index.html | grep -q 824d43a35c7ca1b42b27b273cc7d1e01cc53f5d4512b2f2bad4ce7ac7400f1cd
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
