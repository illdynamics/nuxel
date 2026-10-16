#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/js/transport.js
# previous-hash: 110acd0ad86827e94a6cac0ec723fd4d790b4c89aaca90a38ddb063328aeb825
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js.nuxel-staged
printf '%s  %s\n' 110acd0ad86827e94a6cac0ec723fd4d790b4c89aaca90a38ddb063328aeb825 /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/js/transport.js | grep -q 110acd0ad86827e94a6cac0ec723fd4d790b4c89aaca90a38ddb063328aeb825
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
