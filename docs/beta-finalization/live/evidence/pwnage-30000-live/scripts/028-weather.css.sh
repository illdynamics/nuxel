#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/css/weather.css
# previous-hash: e4706d8a9aab68f40208b8469fb458b6d4b4fa7c9556131d48415332097112a0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-staged
printf '%s  %s\n' e4706d8a9aab68f40208b8469fb458b6d4b4fa7c9556131d48415332097112a0 /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css | grep -q e4706d8a9aab68f40208b8469fb458b6d4b4fa7c9556131d48415332097112a0
echo INSTALL-OK
