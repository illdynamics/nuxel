#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-notifications/notifications.py (service: None, risk: medium)
# staged source: services/nuxel-notifications/src/notifications.py
# previous-hash: d8b8da4b6ff4e703d92ac9bf0a6c70d449528dcaa53c2905fc42ba36b068e0c4
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-notifications/notifications.py)"
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged
printf '%s  %s\n' d8b8da4b6ff4e703d92ac9bf0a6c70d449528dcaa53c2905fc42ba36b068e0c4 /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-staged /usr/lib/nuxel/nuxel-notifications/notifications.py
sha256sum /usr/lib/nuxel/nuxel-notifications/notifications.py | grep -q d8b8da4b6ff4e703d92ac9bf0a6c70d449528dcaa53c2905fc42ba36b068e0c4
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-notifications/notifications.py.nuxel-rollback /usr/lib/nuxel/nuxel-notifications/notifications.py; true; fi
