#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/dbus-1/system.d/org.nuxel.Bridge.conf (service: None, risk: medium)
# staged source: services/nuxel-bridge/dbus/org.nuxel.Bridge.conf
# previous-hash: 0c51d530a6798c966ea82f0438c245aef911f58201a2e8802a30e1aea0242f42
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback ]; then cp -a /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback /etc/dbus-1/system.d/org.nuxel.Bridge.conf; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf ]; then printf 'PREV=%s\n' "$(sha256sum /etc/dbus-1/system.d/org.nuxel.Bridge.conf | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/dbus-1/system.d/org.nuxel.Bridge.conf)"
if [ -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf ] && [ ! -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback ]; then cp -a /etc/dbus-1/system.d/org.nuxel.Bridge.conf /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback; fi
test -f /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-staged
printf '%s  %s\n' 0c51d530a6798c966ea82f0438c245aef911f58201a2e8802a30e1aea0242f42 /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-staged /etc/dbus-1/system.d/org.nuxel.Bridge.conf
sha256sum /etc/dbus-1/system.d/org.nuxel.Bridge.conf | grep -q 0c51d530a6798c966ea82f0438c245aef911f58201a2e8802a30e1aea0242f42
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
