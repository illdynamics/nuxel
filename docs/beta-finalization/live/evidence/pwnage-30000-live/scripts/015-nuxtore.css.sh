#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/css/nuxtore.css
# previous-hash: 3a9f02d78e62d8a62daf09301b7a06da2ef3b131bb34ca76a0faef8a4329c417
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-staged
printf '%s  %s\n' 3a9f02d78e62d8a62daf09301b7a06da2ef3b131bb34ca76a0faef8a4329c417 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css | grep -q 3a9f02d78e62d8a62daf09301b7a06da2ef3b131bb34ca76a0faef8a4329c417
echo INSTALL-OK
