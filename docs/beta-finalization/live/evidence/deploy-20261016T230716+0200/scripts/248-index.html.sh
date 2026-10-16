#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/index.html
# previous-hash: 247f4c173cef0c9f81a7e99a84f9568aa089056c868254871dcd7e3064087c7b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/index.html /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-staged
printf '%s  %s\n' 247f4c173cef0c9f81a7e99a84f9568aa089056c868254871dcd7e3064087c7b /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/index.html | grep -q 247f4c173cef0c9f81a7e99a84f9568aa089056c868254871dcd7e3064087c7b
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
