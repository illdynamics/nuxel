#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/js/mail.js
# previous-hash: 1e6c3dabdf949520e8cd6bb119e350c2f06d96c9ad0f67f13302ed28fc259548
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-staged
printf '%s  %s\n' 1e6c3dabdf949520e8cd6bb119e350c2f06d96c9ad0f67f13302ed28fc259548 /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js | grep -q 1e6c3dabdf949520e8cd6bb119e350c2f06d96c9ad0f67f13302ed28fc259548
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
