#!/bin/sh
# nuxel-http-bridge read-only Tri-Link status endpoint -> /usr/lib/nuxel/nuxel-bridge/tri_link_status.py (service: nuxel-http-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/tri_link_status.py
# previous-hash: 5757d64858c29cc5c6902fa1b80dd6a9eecf5939af0246ffb10fddd5cc0f59ab
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback.pre-deploy-20261027T164310-2129080 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback.pre-deploy-20261027T164310-2129080 /usr/lib/nuxel/nuxel-bridge/tri_link_status.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -x /usr/bin/nuxel-http-bridge
test -d /usr/lib/nuxel/nuxel-bridge
if [ -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/tri_link_status.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/tri_link_status.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/tri_link_status.py /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback.pre-deploy-20261027T164310-2129080 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/tri_link_status.py /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback.pre-deploy-20261027T164310-2129080; fi
test -f /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-staged
printf '%s  %s\n' 5757d64858c29cc5c6902fa1b80dd6a9eecf5939af0246ffb10fddd5cc0f59ab /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/tri_link_status.py
sha256sum /usr/lib/nuxel/nuxel-bridge/tri_link_status.py | grep -q 5757d64858c29cc5c6902fa1b80dd6a9eecf5939af0246ffb10fddd5cc0f59ab
echo INSTALL-OK
