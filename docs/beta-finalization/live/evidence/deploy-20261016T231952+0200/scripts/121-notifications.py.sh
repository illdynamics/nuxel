#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-notifications/notifications.py (service: None, risk: medium)
# staged source: services/nuxel-notifications/src/notifications.py
# previous-hash: d8b8da4b6ff4e703d92ac9bf0a6c70d449528dcaa53c2905fc42ba36b068e0c4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback /usr/lib/nuxel/nuxel-notifications/notifications.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-notifications/notifications.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-notifications/notifications.py)"
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py ] && [ ! -e /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged
printf '%s  %s\n' d8b8da4b6ff4e703d92ac9bf0a6c70d449528dcaa53c2905fc42ba36b068e0c4 /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged /usr/lib/nuxel/nuxel-notifications/notifications.py
sha256sum /usr/lib/nuxel/nuxel-notifications/notifications.py | grep -q d8b8da4b6ff4e703d92ac9bf0a6c70d449528dcaa53c2905fc42ba36b068e0c4
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
