#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/photos/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/index.html
# previous-hash: 21b1ae1f1d593f0faecc723ee715abc5e4de9c4275895cc5f329fc50a1a8be5b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/photos/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/index.html /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/index.html /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-staged
printf '%s  %s\n' 21b1ae1f1d593f0faecc723ee715abc5e4de9c4275895cc5f329fc50a1a8be5b /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/index.html | grep -q 21b1ae1f1d593f0faecc723ee715abc5e4de9c4275895cc5f329fc50a1a8be5b
echo INSTALL-OK
