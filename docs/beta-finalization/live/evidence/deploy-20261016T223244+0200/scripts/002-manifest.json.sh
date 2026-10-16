#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/manifest.json
# previous-hash: bbb2edfa7ef090a6df7d53809eb1540d1f76694b91fb7a889f429ad62bc5606e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged
printf '%s  %s\n' bbb2edfa7ef090a6df7d53809eb1540d1f76694b91fb7a889f429ad62bc5606e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-home/manifest.json | grep -q bbb2edfa7ef090a6df7d53809eb1540d1f76694b91fb7a889f429ad62bc5606e
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
