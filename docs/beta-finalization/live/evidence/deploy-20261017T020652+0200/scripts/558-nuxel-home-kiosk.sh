#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/nuxel-home-kiosk (service: None, risk: medium)
# staged source: shell/nuxel-kiosk/nuxel-home-kiosk
# previous-hash: 50391b34d1f2117e7cb17279a28d6559a6935d10e072a3d73aab7a5f5b038e12
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-home-kiosk.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-home-kiosk.nuxel-rollback /usr/lib/nuxel/nuxel-home-kiosk; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-home-kiosk ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-home-kiosk | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-home-kiosk)"
if [ -e /usr/lib/nuxel/nuxel-home-kiosk ] && [ ! -e /usr/lib/nuxel/nuxel-home-kiosk.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-home-kiosk /usr/lib/nuxel/nuxel-home-kiosk.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-home-kiosk.nuxel-staged
printf '%s  %s\n' 50391b34d1f2117e7cb17279a28d6559a6935d10e072a3d73aab7a5f5b038e12 /usr/lib/nuxel/nuxel-home-kiosk.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-home-kiosk.nuxel-staged /usr/lib/nuxel/nuxel-home-kiosk
sha256sum /usr/lib/nuxel/nuxel-home-kiosk | grep -q 50391b34d1f2117e7cb17279a28d6559a6935d10e072a3d73aab7a5f5b038e12
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
