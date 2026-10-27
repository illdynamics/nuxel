#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/js/mail.js
# previous-hash: 7d95118b98b13162c90489ab8087ced79b35b99ced061aeb1b9a53549b16e70f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-staged
printf '%s  %s\n' 7d95118b98b13162c90489ab8087ced79b35b99ced061aeb1b9a53549b16e70f /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/js/mail.js | grep -q 7d95118b98b13162c90489ab8087ced79b35b99ced061aeb1b9a53549b16e70f
echo INSTALL-OK
