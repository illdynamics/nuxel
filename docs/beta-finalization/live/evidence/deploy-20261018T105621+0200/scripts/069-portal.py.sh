#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-portal/portal.py (service: None, risk: medium)
# staged source: services/nuxel-portal/src/portal.py
# previous-hash: 50e1cb031eb1111ed64a6ec7bc18f5e098db5d469ad299e271247172040cda16
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback /usr/lib/nuxel/nuxel-portal/portal.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-portal/portal.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-portal/portal.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-portal/portal.py)"
if [ -e /usr/lib/nuxel/nuxel-portal/portal.py ] && [ ! -e /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-portal/portal.py /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-staged
printf '%s  %s\n' 50e1cb031eb1111ed64a6ec7bc18f5e098db5d469ad299e271247172040cda16 /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-staged /usr/lib/nuxel/nuxel-portal/portal.py
sha256sum /usr/lib/nuxel/nuxel-portal/portal.py | grep -q 50e1cb031eb1111ed64a6ec7bc18f5e098db5d469ad299e271247172040cda16
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
