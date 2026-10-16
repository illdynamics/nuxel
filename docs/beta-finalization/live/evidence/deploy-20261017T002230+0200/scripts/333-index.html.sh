#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/photos/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/index.html
# previous-hash: 83a911797980cce3164e5bb005aa8852961eb872aa803f5c0899d73376f1ad39
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/photos/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/index.html /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-staged
printf '%s  %s\n' 83a911797980cce3164e5bb005aa8852961eb872aa803f5c0899d73376f1ad39 /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/index.html | grep -q 83a911797980cce3164e5bb005aa8852961eb872aa803f5c0899d73376f1ad39
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
