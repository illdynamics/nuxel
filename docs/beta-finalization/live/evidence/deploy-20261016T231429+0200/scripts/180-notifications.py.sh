#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/notifications.py
# previous-hash: 85f935bce7748c5c66fb4b44db1d7477f6dc38486fbecb16ad92949e2085009a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py.nuxel-staged
printf '%s  %s\n' 85f935bce7748c5c66fb4b44db1d7477f6dc38486fbecb16ad92949e2085009a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/notifications.py | grep -q 85f935bce7748c5c66fb4b44db1d7477f6dc38486fbecb16ad92949e2085009a
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
