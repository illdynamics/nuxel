#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/css/style.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/style.css
# previous-hash: e9904d300ba3ba665cc7adb0568ca87e629e3de5e5196706e316032311adf6ca
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/css/style.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/style.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/style.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/style.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/style.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/style.css /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-staged
printf '%s  %s\n' e9904d300ba3ba665cc7adb0568ca87e629e3de5e5196706e316032311adf6ca /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/style.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/style.css | grep -q e9904d300ba3ba665cc7adb0568ca87e629e3de5e5196706e316032311adf6ca
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
