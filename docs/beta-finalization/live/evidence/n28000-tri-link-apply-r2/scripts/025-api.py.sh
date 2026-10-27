#!/bin/sh
# nuxel-http-bridge read-only Tri-Link status endpoint -> /usr/lib/nuxel/nuxel-bridge/api.py (service: nuxel-http-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/api.py
# previous-hash: b2ffda2169813f1054639f9cf8f30f0981f82de71928b24b7dce74d81a59b8a4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-n28000-tri-link-apply-r2 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-n28000-tri-link-apply-r2 /usr/lib/nuxel/nuxel-bridge/api.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -x /usr/bin/nuxel-http-bridge
test -d /usr/lib/nuxel/nuxel-bridge
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/api.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-n28000-tri-link-apply-r2 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-n28000-tri-link-apply-r2; fi
test -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged
printf '%s  %s\n' b2ffda2169813f1054639f9cf8f30f0981f82de71928b24b7dce74d81a59b8a4 /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/api.py
sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | grep -q b2ffda2169813f1054639f9cf8f30f0981f82de71928b24b7dce74d81a59b8a4
echo INSTALL-OK
