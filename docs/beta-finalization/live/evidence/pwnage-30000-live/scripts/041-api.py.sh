#!/bin/sh
# PWNAGE-30000 bridge persistence and mail transport -> /usr/lib/nuxel/nuxel-bridge/api.py (service: nuxel-http-bridge.service, risk: medium)
# staged source: services/nuxel-bridge/src/api.py
# previous-hash: 6f095bd2bab92e751429c184a925232319f22f274cebccd0ea73b0be7f201434
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/lib/nuxel/nuxel-bridge/api.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/api.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged
printf '%s  %s\n' 6f095bd2bab92e751429c184a925232319f22f274cebccd0ea73b0be7f201434 /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/api.py
sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | grep -q 6f095bd2bab92e751429c184a925232319f22f274cebccd0ea73b0be7f201434
echo INSTALL-OK
