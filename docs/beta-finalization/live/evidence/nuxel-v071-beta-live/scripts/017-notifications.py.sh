#!/bin/sh
# v0.7.1-beta bridge, notification and portal version pins -> /usr/lib/nuxel/nuxel-notifications/notifications.py (service: None, risk: medium)
# staged source: services/nuxel-notifications/src/notifications.py
# previous-hash: 4d2e480847c53ae7b6d49e7b5d99c02450da3bb978790c2f4ba139de99117d14
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback.pre-deploy-20261027T214530-2399261 /usr/lib/nuxel/nuxel-notifications/notifications.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-notifications/notifications.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-notifications/notifications.py)"
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py ] && [ ! -e /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py ] && [ ! -e /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback.pre-deploy-20261027T214530-2399261; fi
test -f /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged
printf '%s  %s\n' 4d2e480847c53ae7b6d49e7b5d99c02450da3bb978790c2f4ba139de99117d14 /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged /usr/lib/nuxel/nuxel-notifications/notifications.py
sha256sum /usr/lib/nuxel/nuxel-notifications/notifications.py | grep -q 4d2e480847c53ae7b6d49e7b5d99c02450da3bb978790c2f4ba139de99117d14
echo INSTALL-OK
