#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/icons/icon-48.png
# previous-hash: 967eb3dc032e2b49fae637aaf5ab584165ca5f2b17b666dd834b32ecde1e701c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png.nuxel-staged
printf '%s  %s\n' 967eb3dc032e2b49fae637aaf5ab584165ca5f2b17b666dd834b32ecde1e701c /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-48.png | grep -q 967eb3dc032e2b49fae637aaf5ab584165ca5f2b17b666dd834b32ecde1e701c
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
