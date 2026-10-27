#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/index.html
# previous-hash: aeee92fd2d56a849fcf5d45cfcf3f94dcf829e3b93e6bcb47c3847bf5ab057d2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-staged
printf '%s  %s\n' aeee92fd2d56a849fcf5d45cfcf3f94dcf829e3b93e6bcb47c3847bf5ab057d2 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html | grep -q aeee92fd2d56a849fcf5d45cfcf3f94dcf829e3b93e6bcb47c3847bf5ab057d2
echo INSTALL-OK
