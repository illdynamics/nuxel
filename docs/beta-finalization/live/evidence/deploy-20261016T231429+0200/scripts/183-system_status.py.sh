#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/system_status.py
# previous-hash: 0a891349d84be08c79c030e5a9f171763ef0bb33c0cf1635dcb0724e4c50301d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-staged
printf '%s  %s\n' 0a891349d84be08c79c030e5a9f171763ef0bb33c0cf1635dcb0724e4c50301d /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/system_status.py | grep -q 0a891349d84be08c79c030e5a9f171763ef0bb33c0cf1635dcb0724e4c50301d
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
