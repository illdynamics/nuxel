#!/bin/sh
# portal host version source -> /usr/lib/nuxel/nuxel-portal/portal.py (service: nuxel-portal, risk: medium)
# staged source: services/nuxel-portal/src/portal.py
# previous-hash: 673b3a683a6e64dff58d2cf4455c8ce5cbd22c6cc5871be521f552bceada874c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback.pre-v070-hotfix ]; then cp -a /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback.pre-v070-hotfix /usr/lib/nuxel/nuxel-portal/portal.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-portal/portal.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-portal/portal.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-portal/portal.py)"
if [ -e /usr/lib/nuxel/nuxel-portal/portal.py ] && [ ! -e /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-portal/portal.py /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-portal/portal.py ] && [ ! -e /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback.pre-v070-hotfix ]; then cp -a /usr/lib/nuxel/nuxel-portal/portal.py /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-rollback.pre-v070-hotfix; fi
test -f /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-staged
printf '%s  %s\n' 673b3a683a6e64dff58d2cf4455c8ce5cbd22c6cc5871be521f552bceada874c /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-portal/portal.py.nuxel-staged /usr/lib/nuxel/nuxel-portal/portal.py
sha256sum /usr/lib/nuxel/nuxel-portal/portal.py | grep -q 673b3a683a6e64dff58d2cf4455c8ce5cbd22c6cc5871be521f552bceada874c
echo INSTALL-OK
