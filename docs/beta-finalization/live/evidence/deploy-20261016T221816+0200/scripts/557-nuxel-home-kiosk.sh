#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/nuxel-home-kiosk (service: None, risk: medium)
# staged source: shell/nuxel-kiosk/nuxel-home-kiosk
# previous-hash: 50391b34d1f2117e7cb17279a28d6559a6935d10e072a3d73aab7a5f5b038e12
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-home-kiosk)"
if [ -e /usr/lib/nuxel/nuxel-home-kiosk ]; then cp -a /usr/lib/nuxel/nuxel-home-kiosk /usr/lib/nuxel/nuxel-home-kiosk.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-home-kiosk.nuxel-staged
printf '%s  %s\n' 50391b34d1f2117e7cb17279a28d6559a6935d10e072a3d73aab7a5f5b038e12 /usr/lib/nuxel/nuxel-home-kiosk.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-home-kiosk.nuxel-staged /usr/lib/nuxel/nuxel-home-kiosk
sha256sum /usr/lib/nuxel/nuxel-home-kiosk | grep -q 50391b34d1f2117e7cb17279a28d6559a6935d10e072a3d73aab7a5f5b038e12
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-home-kiosk.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-home-kiosk.nuxel-rollback /usr/lib/nuxel/nuxel-home-kiosk; true; fi
