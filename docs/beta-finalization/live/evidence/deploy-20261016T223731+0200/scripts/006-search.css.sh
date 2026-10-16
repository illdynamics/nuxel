#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/css/search.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/search.css
# previous-hash: a6487023f747ccb3077cd028ea8b6a14076d1d3a133fd68126508206c38484e0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/css/search.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/search.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/search.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/search.css /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-staged
printf '%s  %s\n' a6487023f747ccb3077cd028ea8b6a14076d1d3a133fd68126508206c38484e0 /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/search.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/search.css | grep -q a6487023f747ccb3077cd028ea8b6a14076d1d3a133fd68126508206c38484e0
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
