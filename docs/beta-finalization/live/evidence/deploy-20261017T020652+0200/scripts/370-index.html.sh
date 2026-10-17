#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/index.html
# previous-hash: 32e648d67203a43043374c72609aeb7b0a3c313c8a6b61db8da8db537b769050
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/index.html /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-staged
printf '%s  %s\n' 32e648d67203a43043374c72609aeb7b0a3c313c8a6b61db8da8db537b769050 /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/index.html | grep -q 32e648d67203a43043374c72609aeb7b0a3c313c8a6b61db8da8db537b769050
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
