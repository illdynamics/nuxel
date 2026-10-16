#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/clock/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/clock/index.html
# previous-hash: 07dcc73726217fb1ba29383ce0b7e67a37a22c55cc7244a3c35f0df3e63dbf95
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/clock/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/clock/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/index.html /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-staged
printf '%s  %s\n' 07dcc73726217fb1ba29383ce0b7e67a37a22c55cc7244a3c35f0df3e63dbf95 /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/index.html | grep -q 07dcc73726217fb1ba29383ce0b7e67a37a22c55cc7244a3c35f0df3e63dbf95
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
