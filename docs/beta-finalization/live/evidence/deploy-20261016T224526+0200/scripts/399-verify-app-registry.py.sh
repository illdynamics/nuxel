#!/bin/sh
# app registry consumers/entries + verifiers -> /usr/lib/nuxel/verify-app-registry.py (service: nuxel-web, risk: low)
# staged source: tools/s10plus/a33/verify-app-registry.py
# previous-hash: d4afac0c5d8e2b94d2691cf3d80191347800f78aba9ebb72654297b601948a66
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/verify-app-registry.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/verify-app-registry.py.nuxel-rollback /usr/lib/nuxel/verify-app-registry.py; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/lib/nuxel/verify-app-registry.py)"
if [ -e /usr/lib/nuxel/verify-app-registry.py ] && [ ! -e /usr/lib/nuxel/verify-app-registry.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/verify-app-registry.py /usr/lib/nuxel/verify-app-registry.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/verify-app-registry.py.nuxel-staged
printf '%s  %s\n' d4afac0c5d8e2b94d2691cf3d80191347800f78aba9ebb72654297b601948a66 /usr/lib/nuxel/verify-app-registry.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/verify-app-registry.py.nuxel-staged /usr/lib/nuxel/verify-app-registry.py
sha256sum /usr/lib/nuxel/verify-app-registry.py | grep -q d4afac0c5d8e2b94d2691cf3d80191347800f78aba9ebb72654297b601948a66
systemctl restart nuxel-web
systemctl is-active nuxel-web
python3 -c "import json;a=json.load(open('/etc/nuxel/app-registry/app_registry.json'));assert a['registry_version']>=4" && test -x /usr/local/bin/verify-app-registry.py
echo INSTALL-OK
