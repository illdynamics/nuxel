#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/main.py
# previous-hash: 9233406676b736c085ae9a3bee48a182c3a133ee27ae2b7c0b56cf2f875f94a3
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-staged
printf '%s  %s\n' 9233406676b736c085ae9a3bee48a182c3a133ee27ae2b7c0b56cf2f875f94a3 /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py | grep -q 9233406676b736c085ae9a3bee48a182c3a133ee27ae2b7c0b56cf2f875f94a3
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py; true; fi
