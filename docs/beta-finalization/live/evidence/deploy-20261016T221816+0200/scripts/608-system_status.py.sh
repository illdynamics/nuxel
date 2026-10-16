#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/system_status.py
# previous-hash: 0a891349d84be08c79c030e5a9f171763ef0bb33c0cf1635dcb0724e4c50301d
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-staged
printf '%s  %s\n' 0a891349d84be08c79c030e5a9f171763ef0bb33c0cf1635dcb0724e4c50301d /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py | grep -q 0a891349d84be08c79c030e5a9f171763ef0bb33c0cf1635dcb0724e4c50301d
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py; true; fi
