#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/__init__.py
# previous-hash: b7ed2f7524d54271d51616353d8319f7c09e66908a6dcbff651f47baec8523f1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py.nuxel-staged
printf '%s  %s\n' b7ed2f7524d54271d51616353d8319f7c09e66908a6dcbff651f47baec8523f1 /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/__init__.py | grep -q b7ed2f7524d54271d51616353d8319f7c09e66908a6dcbff651f47baec8523f1
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
