#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/css/weather.css
# previous-hash: 99fdab92d0a2bf6f12bc0b799c3a79483dd2b30194bd09d343d9a10faa47985c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-staged
printf '%s  %s\n' 99fdab92d0a2bf6f12bc0b799c3a79483dd2b30194bd09d343d9a10faa47985c /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/css/weather.css | grep -q 99fdab92d0a2bf6f12bc0b799c3a79483dd2b30194bd09d343d9a10faa47985c
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
