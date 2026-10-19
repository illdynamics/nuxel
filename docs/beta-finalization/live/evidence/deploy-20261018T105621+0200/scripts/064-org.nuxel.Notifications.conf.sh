#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/dbus-1/system.d/org.nuxel.Notifications.conf (service: None, risk: medium)
# staged source: services/nuxel-notifications/dbus/org.nuxel.Notifications.conf
# previous-hash: 3f64f7388bb6f9324f390074372778786a6a40fa375b44c06ebdc96eecc66710
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/dbus-1/system.d/org.nuxel.Notifications.conf.nuxel-rollback ]; then cp -a /etc/dbus-1/system.d/org.nuxel.Notifications.conf.nuxel-rollback /etc/dbus-1/system.d/org.nuxel.Notifications.conf; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/dbus-1/system.d/org.nuxel.Notifications.conf ]; then printf 'PREV=%s\n' "$(sha256sum /etc/dbus-1/system.d/org.nuxel.Notifications.conf | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/dbus-1/system.d/org.nuxel.Notifications.conf)"
if [ -e /etc/dbus-1/system.d/org.nuxel.Notifications.conf ] && [ ! -e /etc/dbus-1/system.d/org.nuxel.Notifications.conf.nuxel-rollback ]; then cp -a /etc/dbus-1/system.d/org.nuxel.Notifications.conf /etc/dbus-1/system.d/org.nuxel.Notifications.conf.nuxel-rollback; fi
test -f /etc/dbus-1/system.d/org.nuxel.Notifications.conf.nuxel-staged
printf '%s  %s\n' 3f64f7388bb6f9324f390074372778786a6a40fa375b44c06ebdc96eecc66710 /etc/dbus-1/system.d/org.nuxel.Notifications.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/dbus-1/system.d/org.nuxel.Notifications.conf.nuxel-staged /etc/dbus-1/system.d/org.nuxel.Notifications.conf
sha256sum /etc/dbus-1/system.d/org.nuxel.Notifications.conf | grep -q 3f64f7388bb6f9324f390074372778786a6a40fa375b44c06ebdc96eecc66710
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
