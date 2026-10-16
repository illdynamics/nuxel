#!/bin/sh
# Fedora 43 package set reconciliation (data + verifier) -> /usr/local/bin/verify-packages.py (service: None, risk: high)
# staged source: tools/s10plus/a33/verify-packages.py
# previous-hash: f1f3fbe962858c473a03f0fb84c936e6b96c6ee9895d745566cd1ce8d8db0cdc
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/verify-packages.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-packages.py.nuxel-rollback /usr/local/bin/verify-packages.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/local/bin/verify-packages.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/verify-packages.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/verify-packages.py)"
if [ -e /usr/local/bin/verify-packages.py ] && [ ! -e /usr/local/bin/verify-packages.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-packages.py /usr/local/bin/verify-packages.py.nuxel-rollback; fi
test -f /usr/local/bin/verify-packages.py.nuxel-staged
printf '%s  %s\n' f1f3fbe962858c473a03f0fb84c936e6b96c6ee9895d745566cd1ce8d8db0cdc /usr/local/bin/verify-packages.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/verify-packages.py.nuxel-staged /usr/local/bin/verify-packages.py
sha256sum /usr/local/bin/verify-packages.py | grep -q f1f3fbe962858c473a03f0fb84c936e6b96c6ee9895d745566cd1ce8d8db0cdc
( python3 -c "import json;json.load(open('/usr/lib/nuxel/packages-manifest.json'))" ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
