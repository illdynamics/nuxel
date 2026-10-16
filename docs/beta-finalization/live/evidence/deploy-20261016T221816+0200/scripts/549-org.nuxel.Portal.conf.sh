#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/dbus-1/system.d/org.nuxel.Portal.conf (service: None, risk: medium)
# staged source: services/nuxel-portal/dbus/org.nuxel.Portal.conf
# previous-hash: ad9db606f303bd0f5c7dc56c7821c52b6ad5214d60de799c4ce3e4eed8233a95
set -eu
mkdir -p "$(dirname /etc/dbus-1/system.d/org.nuxel.Portal.conf)"
if [ -e /etc/dbus-1/system.d/org.nuxel.Portal.conf ]; then cp -a /etc/dbus-1/system.d/org.nuxel.Portal.conf /etc/dbus-1/system.d/org.nuxel.Portal.conf.nuxel-rollback; fi
test -f /etc/dbus-1/system.d/org.nuxel.Portal.conf.nuxel-staged
printf '%s  %s\n' ad9db606f303bd0f5c7dc56c7821c52b6ad5214d60de799c4ce3e4eed8233a95 /etc/dbus-1/system.d/org.nuxel.Portal.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/dbus-1/system.d/org.nuxel.Portal.conf.nuxel-staged /etc/dbus-1/system.d/org.nuxel.Portal.conf
sha256sum /etc/dbus-1/system.d/org.nuxel.Portal.conf | grep -q ad9db606f303bd0f5c7dc56c7821c52b6ad5214d60de799c4ce3e4eed8233a95
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/dbus-1/system.d/org.nuxel.Portal.conf.nuxel-rollback ]; then cp -a /etc/dbus-1/system.d/org.nuxel.Portal.conf.nuxel-rollback /etc/dbus-1/system.d/org.nuxel.Portal.conf; true; fi
