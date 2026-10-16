#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/recorder/index.html
# previous-hash: 740a3da0ca23b5d29540e984695b7e303dac4b31f4f324a2ed2c0ab1b9a2465d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-staged
printf '%s  %s\n' 740a3da0ca23b5d29540e984695b7e303dac4b31f4f324a2ed2c0ab1b9a2465d /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/index.html | grep -q 740a3da0ca23b5d29540e984695b7e303dac4b31f4f324a2ed2c0ab1b9a2465d
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
