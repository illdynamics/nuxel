#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/_shared/sysinfo.js
# previous-hash: b4d6f61cc0d370a0142b2ff067a62f5b779d33b4d65604da17ff7aad246fe03d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js.nuxel-staged
printf '%s  %s\n' b4d6f61cc0d370a0142b2ff067a62f5b779d33b4d65604da17ff7aad246fe03d /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/_shared/sysinfo.js | grep -q b4d6f61cc0d370a0142b2ff067a62f5b779d33b4d65604da17ff7aad246fe03d
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
