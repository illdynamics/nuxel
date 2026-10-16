#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/bin/nuxel-notifications (service: None, risk: medium)
# staged source: services/nuxel-notifications/bin/nuxel-notifications
# previous-hash: d519a53d05c4607eefeaf135a6bf948a023f531c22875ae3bb7e5bcf45c486b7
set -eu
mkdir -p "$(dirname /usr/bin/nuxel-notifications)"
if [ -e /usr/bin/nuxel-notifications ]; then cp -a /usr/bin/nuxel-notifications /usr/bin/nuxel-notifications.nuxel-rollback; fi
test -f /usr/bin/nuxel-notifications.nuxel-staged
printf '%s  %s\n' d519a53d05c4607eefeaf135a6bf948a023f531c22875ae3bb7e5bcf45c486b7 /usr/bin/nuxel-notifications.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/bin/nuxel-notifications.nuxel-staged /usr/bin/nuxel-notifications
sha256sum /usr/bin/nuxel-notifications | grep -q d519a53d05c4607eefeaf135a6bf948a023f531c22875ae3bb7e5bcf45c486b7
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/bin/nuxel-notifications.nuxel-rollback ]; then cp -a /usr/bin/nuxel-notifications.nuxel-rollback /usr/bin/nuxel-notifications; true; fi
