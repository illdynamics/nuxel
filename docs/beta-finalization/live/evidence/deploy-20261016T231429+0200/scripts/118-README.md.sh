#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-notifications/README.md (service: None, risk: medium)
# staged source: services/nuxel-notifications/README.md
# previous-hash: b0bdc5a098e542ed25656d0b92e3d2ed8ef3b6c0b2c67964f47c0f234617098b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-rollback /usr/lib/nuxel/nuxel-notifications/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-notifications/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-notifications/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-notifications/README.md)"
if [ -e /usr/lib/nuxel/nuxel-notifications/README.md ] && [ ! -e /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-notifications/README.md /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-staged
printf '%s  %s\n' b0bdc5a098e542ed25656d0b92e3d2ed8ef3b6c0b2c67964f47c0f234617098b /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-staged /usr/lib/nuxel/nuxel-notifications/README.md
sha256sum /usr/lib/nuxel/nuxel-notifications/README.md | grep -q b0bdc5a098e542ed25656d0b92e3d2ed8ef3b6c0b2c67964f47c0f234617098b
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
systemctl daemon-reload
echo INSTALL-OK
