#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/weather/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/index.html
# previous-hash: 5b1452aef6b4eb997f4fd855526e98be365899813188502b2c776b0227481d42
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/weather/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/index.html /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/index.html /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-staged
printf '%s  %s\n' 5b1452aef6b4eb997f4fd855526e98be365899813188502b2c776b0227481d42 /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/index.html | grep -q 5b1452aef6b4eb997f4fd855526e98be365899813188502b2c776b0227481d42
echo INSTALL-OK
