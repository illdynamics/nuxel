#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/recorder/index.html
# previous-hash: 3ff480039b0d8248a118f7c14177efd1692c0cb3643ae2925294987232f7e5da
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-staged
printf '%s  %s\n' 3ff480039b0d8248a118f7c14177efd1692c0cb3643ae2925294987232f7e5da /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html | grep -q 3ff480039b0d8248a118f7c14177efd1692c0cb3643ae2925294987232f7e5da
echo INSTALL-OK
