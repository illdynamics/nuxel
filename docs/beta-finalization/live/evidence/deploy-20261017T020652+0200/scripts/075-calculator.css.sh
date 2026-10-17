#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calculator/css/calculator.css
# previous-hash: e2b14f7f31c3384dab8a6885bd7dca7badf9982c552f893ce0447d2970509ff5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-staged
printf '%s  %s\n' e2b14f7f31c3384dab8a6885bd7dca7badf9982c552f893ce0447d2970509ff5 /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css | grep -q e2b14f7f31c3384dab8a6885bd7dca7badf9982c552f893ce0447d2970509ff5
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
