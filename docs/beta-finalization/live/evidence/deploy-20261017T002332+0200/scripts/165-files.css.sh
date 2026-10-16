#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/css/files.css
# previous-hash: 3418757fc1bea072ccbe353a0ffa52c66466ad8e447cdb07ac30cd6d5d3d541c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-staged
printf '%s  %s\n' 3418757fc1bea072ccbe353a0ffa52c66466ad8e447cdb07ac30cd6d5d3d541c /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css | grep -q 3418757fc1bea072ccbe353a0ffa52c66466ad8e447cdb07ac30cd6d5d3d541c
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
