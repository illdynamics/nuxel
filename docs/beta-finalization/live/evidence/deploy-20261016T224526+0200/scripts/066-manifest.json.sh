#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calendar/manifest.json
# previous-hash: a3d613c862faf9c1a73bbdb2ca8c2646023db31be84fe14fc813becb9c927b6b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json.nuxel-staged
printf '%s  %s\n' a3d613c862faf9c1a73bbdb2ca8c2646023db31be84fe14fc813becb9c927b6b /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/manifest.json | grep -q a3d613c862faf9c1a73bbdb2ca8c2646023db31be84fe14fc813becb9c927b6b
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
