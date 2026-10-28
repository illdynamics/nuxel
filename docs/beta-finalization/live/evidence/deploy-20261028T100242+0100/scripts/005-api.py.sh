#!/bin/sh
# Add native in-app Back, activate, and close-foreground bridge routes -> /usr/lib/nuxel/nuxel-bridge/api.py (service: nuxel-http-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/api.py
# previous-hash: 6bfe6c850186965214c3c42178e6b976b78bd95b7ccb69eec61b8dc5378d26d3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261028T100242-2721366 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261028T100242-2721366 /usr/lib/nuxel/nuxel-bridge/api.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/api.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261028T100242-2721366 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261028T100242-2721366; fi
test -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged
printf '%s  %s\n' 6bfe6c850186965214c3c42178e6b976b78bd95b7ccb69eec61b8dc5378d26d3 /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/api.py
sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | grep -q 6bfe6c850186965214c3c42178e6b976b78bd95b7ccb69eec61b8dc5378d26d3
echo INSTALL-OK
