#!/bin/sh
# v0.7.1-beta bridge, notification and portal version pins -> /usr/lib/nuxel/nuxel-portal/portal.py (service: None, risk: medium)
# staged source: services/nuxel-portal/src/portal.py
# previous-hash: 78fe97fa4e1f86069745db7ba679d4e55e86a20d2bb20201af49feb889a121c2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback.pre-deploy-20261027T214523-2399095 /usr/lib/nuxel/nuxel-portal/portal.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-portal/portal.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-portal/portal.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-portal/portal.py)"
if [ -e /usr/lib/nuxel/nuxel-portal/portal.py ] && [ ! -e /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-portal/portal.py /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-portal/portal.py ] && [ ! -e /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/lib/nuxel/nuxel-portal/portal.py /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback.pre-deploy-20261027T214523-2399095; fi
test -f /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-staged
printf '%s  %s\n' 78fe97fa4e1f86069745db7ba679d4e55e86a20d2bb20201af49feb889a121c2 /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-staged /usr/lib/nuxel/nuxel-portal/portal.py
sha256sum /usr/lib/nuxel/nuxel-portal/portal.py | grep -q 78fe97fa4e1f86069745db7ba679d4e55e86a20d2bb20201af49feb889a121c2
echo INSTALL-OK
