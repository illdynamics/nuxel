#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/launcher_grid.py
# previous-hash: e169e15ae403bf29332cafbcabc8ae75c81254562ba87c5f00c2b8074bcef8aa
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-staged
printf '%s  %s\n' e169e15ae403bf29332cafbcabc8ae75c81254562ba87c5f00c2b8074bcef8aa /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/launcher_grid.py | grep -q e169e15ae403bf29332cafbcabc8ae75c81254562ba87c5f00c2b8074bcef8aa
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
