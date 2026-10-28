#!/bin/sh
# Bridge phone-status battery fallback and Full-vs-Charging truth -> /usr/lib/nuxel/nuxel-bridge/api.py (service: nuxel-http-bridge, risk: low)
# staged source: services/nuxel-bridge/src/api.py
# previous-hash: 5e2323bd88eb6df47711ed42293e0b08f7d87d7ad9681b480585bafdd625c2d9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T222436-2425021 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T222436-2425021 /usr/lib/nuxel/nuxel-bridge/api.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/api.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T222436-2425021 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-deploy-20261027T222436-2425021; fi
test -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged
printf '%s  %s\n' 5e2323bd88eb6df47711ed42293e0b08f7d87d7ad9681b480585bafdd625c2d9 /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/api.py
sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | grep -q 5e2323bd88eb6df47711ed42293e0b08f7d87d7ad9681b480585bafdd625c2d9
echo INSTALL-OK
