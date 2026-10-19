#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/verify-app-inventory.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/verify-app-inventory.py
# previous-hash: 3c5d90250072c4b07b79afa732d2f2e10f7f7c1bc7946cedfb2c3443bdf4ae63
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/verify-app-inventory.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-app-inventory.py.nuxel-rollback /usr/local/bin/verify-app-inventory.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/verify-app-inventory.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/verify-app-inventory.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/verify-app-inventory.py)"
if [ -e /usr/local/bin/verify-app-inventory.py ] && [ ! -e /usr/local/bin/verify-app-inventory.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-app-inventory.py /usr/local/bin/verify-app-inventory.py.nuxel-rollback; fi
test -f /usr/local/bin/verify-app-inventory.py.nuxel-staged
printf '%s  %s\n' 3c5d90250072c4b07b79afa732d2f2e10f7f7c1bc7946cedfb2c3443bdf4ae63 /usr/local/bin/verify-app-inventory.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/verify-app-inventory.py.nuxel-staged /usr/local/bin/verify-app-inventory.py
sha256sum /usr/local/bin/verify-app-inventory.py | grep -q 3c5d90250072c4b07b79afa732d2f2e10f7f7c1bc7946cedfb2c3443bdf4ae63
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
