#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/dbus_client.py
# previous-hash: 114143fa16090de83ebbf7836e2fdb853798ac651688507ac6e1545844f846bf
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-staged
printf '%s  %s\n' 114143fa16090de83ebbf7836e2fdb853798ac651688507ac6e1545844f846bf /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py | grep -q 114143fa16090de83ebbf7836e2fdb853798ac651688507ac6e1545844f846bf
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/dbus_client.py; true; fi
