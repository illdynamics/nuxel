#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/app_model.py
# previous-hash: 587c3111581ce5ef11507a0cf58a4d844dea43223bb30750f796bbaa9e2a9392
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-staged
printf '%s  %s\n' 587c3111581ce5ef11507a0cf58a4d844dea43223bb30750f796bbaa9e2a9392 /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py | grep -q 587c3111581ce5ef11507a0cf58a4d844dea43223bb30750f796bbaa9e2a9392
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
