#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/verify-app-registry.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/verify-app-registry.py
# previous-hash: d4afac0c5d8e2b94d2691cf3d80191347800f78aba9ebb72654297b601948a66
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/verify-app-registry.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-app-registry.py.nuxel-rollback /usr/local/bin/verify-app-registry.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/verify-app-registry.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/verify-app-registry.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/verify-app-registry.py)"
if [ -e /usr/local/bin/verify-app-registry.py ] && [ ! -e /usr/local/bin/verify-app-registry.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-app-registry.py /usr/local/bin/verify-app-registry.py.nuxel-rollback; fi
test -f /usr/local/bin/verify-app-registry.py.nuxel-staged
printf '%s  %s\n' d4afac0c5d8e2b94d2691cf3d80191347800f78aba9ebb72654297b601948a66 /usr/local/bin/verify-app-registry.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/verify-app-registry.py.nuxel-staged /usr/local/bin/verify-app-registry.py
sha256sum /usr/local/bin/verify-app-registry.py | grep -q d4afac0c5d8e2b94d2691cf3d80191347800f78aba9ebb72654297b601948a66
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
