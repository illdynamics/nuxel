#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/icons/icon-72.png
# previous-hash: 2e1da222295f8749e6a78082d056941ad4b7e0d8aa7ca611c47d7bacbb8fbe17
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png.nuxel-staged
printf '%s  %s\n' 2e1da222295f8749e6a78082d056941ad4b7e0d8aa7ca611c47d7bacbb8fbe17 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-72.png | grep -q 2e1da222295f8749e6a78082d056941ad4b7e0d8aa7ca611c47d7bacbb8fbe17
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
