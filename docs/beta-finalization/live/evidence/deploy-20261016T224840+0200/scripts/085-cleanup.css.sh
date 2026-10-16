#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/css/cleanup.css
# previous-hash: 8ed47af64926f34e80a462e770b9b48084ca9efd7a9885845c0648935cc36563
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css.nuxel-staged
printf '%s  %s\n' 8ed47af64926f34e80a462e770b9b48084ca9efd7a9885845c0648935cc36563 /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/css/cleanup.css | grep -q 8ed47af64926f34e80a462e770b9b48084ca9efd7a9885845c0648935cc36563
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
