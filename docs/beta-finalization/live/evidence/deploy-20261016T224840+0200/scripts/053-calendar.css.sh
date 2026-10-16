#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calendar/css/calendar.css
# previous-hash: cd7b98b610fab074d42b716695bd0bb6db5308d70b6b05787d052d1102db25a0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-staged
printf '%s  %s\n' cd7b98b610fab074d42b716695bd0bb6db5308d70b6b05787d052d1102db25a0 /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css | grep -q cd7b98b610fab074d42b716695bd0bb6db5308d70b6b05787d052d1102db25a0
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
