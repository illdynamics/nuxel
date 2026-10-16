#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-web-server.py (service: None, risk: medium)
# staged source: services/nuxel-web/bin/nuxel-web-server.py
# previous-hash: b17fb3e700ed3918691a395895090ca68eab5fe45b1f9a01a63a270f27072520
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-web-server.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-web-server.py.nuxel-rollback /usr/lib/nuxel/nuxel-web-server.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-web-server.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-web-server.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-web-server.py)"
if [ -e /usr/lib/nuxel/nuxel-web-server.py ] && [ ! -e /usr/lib/nuxel/nuxel-web-server.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-web-server.py /usr/lib/nuxel/nuxel-web-server.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-web-server.py.nuxel-staged
printf '%s  %s\n' b17fb3e700ed3918691a395895090ca68eab5fe45b1f9a01a63a270f27072520 /usr/lib/nuxel/nuxel-web-server.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-web-server.py.nuxel-staged /usr/lib/nuxel/nuxel-web-server.py
sha256sum /usr/lib/nuxel/nuxel-web-server.py | grep -q b17fb3e700ed3918691a395895090ca68eab5fe45b1f9a01a63a270f27072520
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
