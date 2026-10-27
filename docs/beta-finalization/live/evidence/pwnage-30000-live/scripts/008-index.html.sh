#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/files/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/index.html
# previous-hash: 4119d5331e69f098bee3334752f81de6dec3f65ed4b7175966e70df28c88a1d8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/files/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/index.html /usr/share/nuxel/pwa/nuxel-apps/files/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/index.html /usr/share/nuxel/pwa/nuxel-apps/files/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/index.html.nuxel-staged
printf '%s  %s\n' 4119d5331e69f098bee3334752f81de6dec3f65ed4b7175966e70df28c88a1d8 /usr/share/nuxel/pwa/nuxel-apps/files/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/index.html | grep -q 4119d5331e69f098bee3334752f81de6dec3f65ed4b7175966e70df28c88a1d8
echo INSTALL-OK
