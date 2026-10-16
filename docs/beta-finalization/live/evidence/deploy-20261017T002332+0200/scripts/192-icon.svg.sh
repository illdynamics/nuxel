#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/icons/icon.svg
# previous-hash: 84a735e7f67cda49599ad7519f18324b3fcb7441e208efcccafe10f398a80913
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg.nuxel-staged
printf '%s  %s\n' 84a735e7f67cda49599ad7519f18324b3fcb7441e208efcccafe10f398a80913 /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon.svg | grep -q 84a735e7f67cda49599ad7519f18324b3fcb7441e208efcccafe10f398a80913
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
