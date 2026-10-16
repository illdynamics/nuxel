#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/launcher_grid.py
# previous-hash: e169e15ae403bf29332cafbcabc8ae75c81254562ba87c5f00c2b8074bcef8aa
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-staged
printf '%s  %s\n' e169e15ae403bf29332cafbcabc8ae75c81254562ba87c5f00c2b8074bcef8aa /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py | grep -q e169e15ae403bf29332cafbcabc8ae75c81254562ba87c5f00c2b8074bcef8aa
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py; true; fi
