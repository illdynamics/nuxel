#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/penguinterface/icons/icon-384.png
# previous-hash: de687ca8fcc64d4ea34e256a2b298ea89b1f4a17d7a92ce74c6ca83e9634a55e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png.nuxel-staged
printf '%s  %s\n' de687ca8fcc64d4ea34e256a2b298ea89b1f4a17d7a92ce74c6ca83e9634a55e /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-384.png | grep -q de687ca8fcc64d4ea34e256a2b298ea89b1f4a17d7a92ce74c6ca83e9634a55e
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
