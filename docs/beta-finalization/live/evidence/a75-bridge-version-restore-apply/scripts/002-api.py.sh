#!/bin/sh
# nuxel-http-bridge REST code (version pin) -> /usr/lib/nuxel/nuxel-bridge/api.py (service: nuxel-http-bridge.service, risk: medium)
# staged source: services/nuxel-bridge/src/api.py
# previous-hash: 64be1b6a550053c6c5f8e6b90d27718d4605ed74d5ce1f74b3757d5979f25227
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback /usr/lib/nuxel/nuxel-bridge/api.py; systemctl restart nuxel-http-bridge.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/api.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged
printf '%s  %s\n' 64be1b6a550053c6c5f8e6b90d27718d4605ed74d5ce1f74b3757d5979f25227 /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/api.py
sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | grep -q 64be1b6a550053c6c5f8e6b90d27718d4605ed74d5ce1f74b3757d5979f25227
systemctl restart nuxel-http-bridge.service
systemctl is-active nuxel-http-bridge.service
echo INSTALL-OK
