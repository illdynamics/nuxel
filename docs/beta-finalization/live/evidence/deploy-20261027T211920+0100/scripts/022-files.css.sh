#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/css/files.css
# previous-hash: 62039d0894b4f84468345458f2161fbdd88966895ff43a77a582c7733e4ce2e5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-staged
printf '%s  %s\n' 62039d0894b4f84468345458f2161fbdd88966895ff43a77a582c7733e4ce2e5 /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css | grep -q 62039d0894b4f84468345458f2161fbdd88966895ff43a77a582c7733e4ce2e5
echo INSTALL-OK
