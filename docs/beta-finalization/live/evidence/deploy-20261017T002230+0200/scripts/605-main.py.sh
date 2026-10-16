#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/main.py
# previous-hash: 9233406676b736c085ae9a3bee48a182c3a133ee27ae2b7c0b56cf2f875f94a3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-staged
printf '%s  %s\n' 9233406676b736c085ae9a3bee48a182c3a133ee27ae2b7c0b56cf2f875f94a3 /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/main.py | grep -q 9233406676b736c085ae9a3bee48a182c3a133ee27ae2b7c0b56cf2f875f94a3
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
