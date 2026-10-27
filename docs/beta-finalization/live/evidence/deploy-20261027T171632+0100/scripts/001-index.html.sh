#!/bin/sh
# Settings PWA (Bluetooth/Displays/Audio pages) + Home QS + shared bridge client -> /usr/share/nuxel/pwa/nuxel-apps/settings/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/index.html
# previous-hash: 2266b153d003f95fb3db69c29d049149ef0608d77b431649052e34c8f4e33ab2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback.pre-deploy-20261027T171632-2151780 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback.pre-deploy-20261027T171632-2151780 /usr/share/nuxel/pwa/nuxel-apps/settings/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/index.html /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback.pre-deploy-20261027T171632-2151780 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/index.html /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback.pre-deploy-20261027T171632-2151780; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-staged
printf '%s  %s\n' 2266b153d003f95fb3db69c29d049149ef0608d77b431649052e34c8f4e33ab2 /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/index.html | grep -q 2266b153d003f95fb3db69c29d049149ef0608d77b431649052e34c8f4e33ab2
echo INSTALL-OK
