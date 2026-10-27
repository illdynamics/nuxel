#!/bin/sh
# nuxel-http-bridge root hardware providers (audio/display/bluetooth-power) -> /usr/lib/nuxel/nuxel-bridge/api.py (service: nuxel-http-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/api.py
# previous-hash: 55628f717ef5496384ac92b228d81766cfedbdfd0201057e91e540448df5fe9d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T173720-2158877 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T173720-2158877 /usr/lib/nuxel/nuxel-bridge/api.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -d /usr/lib/nuxel/nuxel-bridge
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/api.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T173720-2158877 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T173720-2158877; fi
test -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged
printf '%s  %s\n' 55628f717ef5496384ac92b228d81766cfedbdfd0201057e91e540448df5fe9d /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/api.py
sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | grep -q 55628f717ef5496384ac92b228d81766cfedbdfd0201057e91e540448df5fe9d
echo INSTALL-OK
