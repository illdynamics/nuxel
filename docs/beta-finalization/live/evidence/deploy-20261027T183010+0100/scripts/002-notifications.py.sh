#!/bin/sh
# notifications host version source -> /usr/lib/nuxel/nuxel-notifications/notifications.py (service: nuxel-notifications, risk: medium)
# staged source: services/nuxel-notifications/src/notifications.py
# previous-hash: 7dc49d6acc43c6818c54ddb1f99a6e903c1d0de4b23a6433c20d0424ef27094a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback.pre-deploy-20261027T183010-2206706 ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback.pre-deploy-20261027T183010-2206706 /usr/lib/nuxel/nuxel-notifications/notifications.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-notifications/notifications.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-notifications/notifications.py)"
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py ] && [ ! -e /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py ] && [ ! -e /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback.pre-deploy-20261027T183010-2206706 ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback.pre-deploy-20261027T183010-2206706; fi
test -f /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged
printf '%s  %s\n' 7dc49d6acc43c6818c54ddb1f99a6e903c1d0de4b23a6433c20d0424ef27094a /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged /usr/lib/nuxel/nuxel-notifications/notifications.py
sha256sum /usr/lib/nuxel/nuxel-notifications/notifications.py | grep -q 7dc49d6acc43c6818c54ddb1f99a6e903c1d0de4b23a6433c20d0424ef27094a
echo INSTALL-OK
