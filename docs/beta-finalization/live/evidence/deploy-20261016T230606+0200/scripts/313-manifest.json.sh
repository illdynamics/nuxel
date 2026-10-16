#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/recorder/manifest.json
# previous-hash: 05ee3ac026b4349e0c15660e70be19e616c9c4c785c983ad1565080524e1142e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json.nuxel-staged
printf '%s  %s\n' 05ee3ac026b4349e0c15660e70be19e616c9c4c785c983ad1565080524e1142e /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/manifest.json | grep -q 05ee3ac026b4349e0c15660e70be19e616c9c4c785c983ad1565080524e1142e
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
