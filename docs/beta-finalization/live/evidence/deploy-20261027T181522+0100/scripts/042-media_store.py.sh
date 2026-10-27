#!/bin/sh
# nuxel-bridge Bluetooth/location providers and media store -> /usr/lib/nuxel/nuxel-bridge/media_store.py (service: nuxel-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/media_store.py
# previous-hash: 87029f4c186b850c1e0f0872b44e9c2132fec0a79ec6fc971804fea84a7234a0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/media_store.py.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/media_store.py.nuxel-rollback.pre-deploy-20261027T181522-2198480 /usr/lib/nuxel/nuxel-bridge/media_store.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/media_store.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/media_store.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/media_store.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/media_store.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/media_store.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/media_store.py /usr/lib/nuxel/nuxel-bridge/media_store.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/media_store.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/media_store.py.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/media_store.py /usr/lib/nuxel/nuxel-bridge/media_store.py.nuxel-rollback.pre-deploy-20261027T181522-2198480; fi
test -f /usr/lib/nuxel/nuxel-bridge/media_store.py.nuxel-staged
printf '%s  %s\n' 87029f4c186b850c1e0f0872b44e9c2132fec0a79ec6fc971804fea84a7234a0 /usr/lib/nuxel/nuxel-bridge/media_store.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/media_store.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/media_store.py
sha256sum /usr/lib/nuxel/nuxel-bridge/media_store.py | grep -q 87029f4c186b850c1e0f0872b44e9c2132fec0a79ec6fc971804fea84a7234a0
echo INSTALL-OK
