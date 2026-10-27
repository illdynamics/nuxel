#!/bin/sh
# PWNAGE-30000 bridge persistence and mail transport -> /usr/lib/nuxel/nuxel-bridge/pwa_store.py (service: nuxel-http-bridge.service, risk: medium)
# staged source: services/nuxel-bridge/src/pwa_store.py
# previous-hash: 555a1bac9e611ca0672358f21aff4c18c08e6be1da0f76efdfcbc98c3f546041
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/pwa_store.py.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/pwa_store.py.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/lib/nuxel/nuxel-bridge/pwa_store.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/pwa_store.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/pwa_store.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/pwa_store.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/pwa_store.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/pwa_store.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/pwa_store.py /usr/lib/nuxel/nuxel-bridge/pwa_store.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/pwa_store.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/pwa_store.py.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/pwa_store.py /usr/lib/nuxel/nuxel-bridge/pwa_store.py.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/lib/nuxel/nuxel-bridge/pwa_store.py.nuxel-staged
printf '%s  %s\n' 555a1bac9e611ca0672358f21aff4c18c08e6be1da0f76efdfcbc98c3f546041 /usr/lib/nuxel/nuxel-bridge/pwa_store.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/pwa_store.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/pwa_store.py
sha256sum /usr/lib/nuxel/nuxel-bridge/pwa_store.py | grep -q 555a1bac9e611ca0672358f21aff4c18c08e6be1da0f76efdfcbc98c3f546041
echo INSTALL-OK
