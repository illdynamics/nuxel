#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/bin/nuxel-bridge (service: None, risk: medium)
# staged source: services/nuxel-bridge/bin/nuxel-bridge
# previous-hash: 004847ca71df3ad46007206b9f85128a1d4787a547bdbd8c793df66b61e65e01
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/bin/nuxel-bridge.nuxel-rollback ]; then cp -a /usr/bin/nuxel-bridge.nuxel-rollback /usr/bin/nuxel-bridge; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/bin/nuxel-bridge ]; then printf 'PREV=%s\n' "$(sha256sum /usr/bin/nuxel-bridge | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/bin/nuxel-bridge)"
if [ -e /usr/bin/nuxel-bridge ] && [ ! -e /usr/bin/nuxel-bridge.nuxel-rollback ]; then cp -a /usr/bin/nuxel-bridge /usr/bin/nuxel-bridge.nuxel-rollback; fi
test -f /usr/bin/nuxel-bridge.nuxel-staged
printf '%s  %s\n' 004847ca71df3ad46007206b9f85128a1d4787a547bdbd8c793df66b61e65e01 /usr/bin/nuxel-bridge.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/bin/nuxel-bridge.nuxel-staged /usr/bin/nuxel-bridge
sha256sum /usr/bin/nuxel-bridge | grep -q 004847ca71df3ad46007206b9f85128a1d4787a547bdbd8c793df66b61e65e01
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
