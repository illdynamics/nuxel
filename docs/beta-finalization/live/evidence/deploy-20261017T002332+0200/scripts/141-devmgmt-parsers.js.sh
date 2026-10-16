#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js
# previous-hash: b871e9720233bd41da8e6b97cee461d81f25b3bbe3ce4c303a3c729be4092829
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js.nuxel-staged
printf '%s  %s\n' b871e9720233bd41da8e6b97cee461d81f25b3bbe3ce4c303a3c729be4092829 /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt-parsers.js | grep -q b871e9720233bd41da8e6b97cee461d81f25b3bbe3ce4c303a3c729be4092829
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
