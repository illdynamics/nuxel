#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/settings.css
# previous-hash: f077cb2bb4e602e36dedf11a2474c5f5103d495f150500ff542c67a0555834dd
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-staged
printf '%s  %s\n' f077cb2bb4e602e36dedf11a2474c5f5103d495f150500ff542c67a0555834dd /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css | grep -q f077cb2bb4e602e36dedf11a2474c5f5103d495f150500ff542c67a0555834dd
echo INSTALL-OK
