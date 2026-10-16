#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/index.html
# previous-hash: 70e3bffce23425135d54bd3bb078318a5f8ae37f7884f62738a72c9d85631dce
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/index.html /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-staged
printf '%s  %s\n' 70e3bffce23425135d54bd3bb078318a5f8ae37f7884f62738a72c9d85631dce /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/index.html | grep -q 70e3bffce23425135d54bd3bb078318a5f8ae37f7884f62738a72c9d85631dce
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
