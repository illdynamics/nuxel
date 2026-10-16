#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/app_launcher.py
# previous-hash: 52633e1e3d7a41a89b00a8b34fe8dc4ca83a0df21e9254526bd8e9baa622d5ea
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py.nuxel-staged
printf '%s  %s\n' 52633e1e3d7a41a89b00a8b34fe8dc4ca83a0df21e9254526bd8e9baa622d5ea /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_launcher.py | grep -q 52633e1e3d7a41a89b00a8b34fe8dc4ca83a0df21e9254526bd8e9baa622d5ea
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
