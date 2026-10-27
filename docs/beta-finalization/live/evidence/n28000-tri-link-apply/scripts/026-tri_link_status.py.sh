#!/bin/sh
# nuxel-http-bridge read-only Tri-Link status endpoint -> /usr/lib/nuxel/nuxel-bridge/tri_link_status.py (service: nuxel-http-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/tri_link_status.py
# previous-hash: 2a5a17e4eb11d8d7943f2ff661af9ee96259d575ada9126884a8a52215c69d67
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback.pre-n28000-tri-link-apply ]; then cp -a /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback.pre-n28000-tri-link-apply /usr/lib/nuxel/nuxel-bridge/tri_link_status.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -x /usr/bin/nuxel-http-bridge
test -d /usr/lib/nuxel/nuxel-bridge
if [ -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/tri_link_status.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/tri_link_status.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/tri_link_status.py /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback.pre-n28000-tri-link-apply ]; then cp -a /usr/lib/nuxel/nuxel-bridge/tri_link_status.py /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-rollback.pre-n28000-tri-link-apply; fi
test -f /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-staged
printf '%s  %s\n' 2a5a17e4eb11d8d7943f2ff661af9ee96259d575ada9126884a8a52215c69d67 /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/tri_link_status.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/tri_link_status.py
sha256sum /usr/lib/nuxel/nuxel-bridge/tri_link_status.py | grep -q 2a5a17e4eb11d8d7943f2ff661af9ee96259d575ada9126884a8a52215c69d67
echo INSTALL-OK
