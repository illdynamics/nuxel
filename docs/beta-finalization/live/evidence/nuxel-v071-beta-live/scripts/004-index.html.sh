#!/bin/sh
# v0.7.1-beta PWA version pins and launcher cache namespace -> /usr/share/nuxel/pwa/nuxel-home/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/index.html
# previous-hash: 3f782e09313cadbd813f68f1c8136341c0c12edcdbf9301d18f5dd5708d9a920
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T214530-2399261 /usr/share/nuxel/pwa/nuxel-home/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T214530-2399261; fi
test -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged
printf '%s  %s\n' 3f782e09313cadbd813f68f1c8136341c0c12edcdbf9301d18f5dd5708d9a920 /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | grep -q 3f782e09313cadbd813f68f1c8136341c0c12edcdbf9301d18f5dd5708d9a920
echo INSTALL-OK
