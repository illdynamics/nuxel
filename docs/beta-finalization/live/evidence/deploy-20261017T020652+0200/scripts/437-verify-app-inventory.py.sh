#!/bin/sh
# app registry consumers/entries + verifiers -> /usr/lib/nuxel/verify-app-inventory.py (service: nuxel-web, risk: low)
# staged source: tools/s10plus/a33/verify-app-inventory.py
# previous-hash: f18ccad895d647ed7b5d5f63d6b8f7ee1ee9ea3dc91cb0a369764cb85b9da059
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/verify-app-inventory.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/verify-app-inventory.py.nuxel-rollback /usr/lib/nuxel/verify-app-inventory.py; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/verify-app-inventory.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/verify-app-inventory.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/verify-app-inventory.py)"
if [ -e /usr/lib/nuxel/verify-app-inventory.py ] && [ ! -e /usr/lib/nuxel/verify-app-inventory.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/verify-app-inventory.py /usr/lib/nuxel/verify-app-inventory.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/verify-app-inventory.py.nuxel-staged
printf '%s  %s\n' f18ccad895d647ed7b5d5f63d6b8f7ee1ee9ea3dc91cb0a369764cb85b9da059 /usr/lib/nuxel/verify-app-inventory.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/verify-app-inventory.py.nuxel-staged /usr/lib/nuxel/verify-app-inventory.py
sha256sum /usr/lib/nuxel/verify-app-inventory.py | grep -q f18ccad895d647ed7b5d5f63d6b8f7ee1ee9ea3dc91cb0a369764cb85b9da059
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
