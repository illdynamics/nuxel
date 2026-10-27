#!/bin/sh
# nuxel-bridge Bluetooth/location providers and media store -> /etc/dbus-1/system.d/org.nuxel.Bridge.conf (service: nuxel-bridge, risk: medium)
# staged source: services/nuxel-bridge/dbus/org.nuxel.Bridge.conf
# previous-hash: 7eddb60ce4291759a3a3de365d27df1c690cb0538dfc323bf37b1618c2cc1e21
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback.pre-v070-delta-release3 /etc/dbus-1/system.d/org.nuxel.Bridge.conf; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf ]; then printf 'PREV=%s\n' "$(sha256sum /etc/dbus-1/system.d/org.nuxel.Bridge.conf | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/dbus-1/system.d/org.nuxel.Bridge.conf)"
if [ -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf ] && [ ! -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback ]; then cp -a /etc/dbus-1/system.d/org.nuxel.Bridge.conf /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback; fi
if [ -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf ] && [ ! -e /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /etc/dbus-1/system.d/org.nuxel.Bridge.conf /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-rollback.pre-v070-delta-release3; fi
test -f /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-staged
printf '%s  %s\n' 7eddb60ce4291759a3a3de365d27df1c690cb0538dfc323bf37b1618c2cc1e21 /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/dbus-1/system.d/org.nuxel.Bridge.conf.nuxel-staged /etc/dbus-1/system.d/org.nuxel.Bridge.conf
sha256sum /etc/dbus-1/system.d/org.nuxel.Bridge.conf | grep -q 7eddb60ce4291759a3a3de365d27df1c690cb0538dfc323bf37b1618c2cc1e21
echo INSTALL-OK
