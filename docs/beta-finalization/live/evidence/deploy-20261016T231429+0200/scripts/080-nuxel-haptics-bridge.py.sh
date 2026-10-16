#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-haptics-bridge.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-haptics-bridge.py
# previous-hash: d0c9027396b0c13ed974a7a9718d8bf2e8f80e7c9e40e9b0786d88e13d9fee47
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-haptics-bridge.py.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-haptics-bridge.py.nuxel-rollback /usr/local/bin/nuxel-haptics-bridge.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-haptics-bridge.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-haptics-bridge.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-haptics-bridge.py)"
if [ -e /usr/local/bin/nuxel-haptics-bridge.py ] && [ ! -e /usr/local/bin/nuxel-haptics-bridge.py.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-haptics-bridge.py /usr/local/bin/nuxel-haptics-bridge.py.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-haptics-bridge.py.nuxel-staged
printf '%s  %s\n' d0c9027396b0c13ed974a7a9718d8bf2e8f80e7c9e40e9b0786d88e13d9fee47 /usr/local/bin/nuxel-haptics-bridge.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-haptics-bridge.py.nuxel-staged /usr/local/bin/nuxel-haptics-bridge.py
sha256sum /usr/local/bin/nuxel-haptics-bridge.py | grep -q d0c9027396b0c13ed974a7a9718d8bf2e8f80e7c9e40e9b0786d88e13d9fee47
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
