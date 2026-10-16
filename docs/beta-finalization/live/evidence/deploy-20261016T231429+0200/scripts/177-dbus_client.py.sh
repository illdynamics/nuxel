#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/dbus_client.py
# previous-hash: 114143fa16090de83ebbf7836e2fdb853798ac651688507ac6e1545844f846bf
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-staged
printf '%s  %s\n' 114143fa16090de83ebbf7836e2fdb853798ac651688507ac6e1545844f846bf /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py | grep -q 114143fa16090de83ebbf7836e2fdb853798ac651688507ac6e1545844f846bf
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
