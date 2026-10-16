#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/bin/nuxel-http-bridge (service: None, risk: medium)
# staged source: services/nuxel-bridge/bin/nuxel-http-bridge
# previous-hash: e16c4faff5540d1b3667b7a158983b86ca0d9bd03822689f3fd084fa7236a50f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/bin/nuxel-http-bridge.nuxel-rollback ]; then cp -a /usr/bin/nuxel-http-bridge.nuxel-rollback /usr/bin/nuxel-http-bridge; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/bin/nuxel-http-bridge ]; then printf 'PREV=%s\n' "$(sha256sum /usr/bin/nuxel-http-bridge | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/bin/nuxel-http-bridge)"
if [ -e /usr/bin/nuxel-http-bridge ] && [ ! -e /usr/bin/nuxel-http-bridge.nuxel-rollback ]; then cp -a /usr/bin/nuxel-http-bridge /usr/bin/nuxel-http-bridge.nuxel-rollback; fi
test -f /usr/bin/nuxel-http-bridge.nuxel-staged
printf '%s  %s\n' e16c4faff5540d1b3667b7a158983b86ca0d9bd03822689f3fd084fa7236a50f /usr/bin/nuxel-http-bridge.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/bin/nuxel-http-bridge.nuxel-staged /usr/bin/nuxel-http-bridge
sha256sum /usr/bin/nuxel-http-bridge | grep -q e16c4faff5540d1b3667b7a158983b86ca0d9bd03822689f3fd084fa7236a50f
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
