#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/css/devmgmt.css
# previous-hash: 0f8de47ebd852c147d04e9be64e6031dd0a7c72797e054eb4c3dba4c6d8515e3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css.nuxel-staged
printf '%s  %s\n' 0f8de47ebd852c147d04e9be64e6031dd0a7c72797e054eb4c3dba4c6d8515e3 /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/css/devmgmt.css | grep -q 0f8de47ebd852c147d04e9be64e6031dd0a7c72797e054eb4c3dba4c6d8515e3
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
