#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/settings_store.py
# previous-hash: bf3e123b7332e839fbf9716bac8828e60c265db8b5e5c1c2116ba1e30de2e694
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-staged
printf '%s  %s\n' bf3e123b7332e839fbf9716bac8828e60c265db8b5e5c1c2116ba1e30de2e694 /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py | grep -q bf3e123b7332e839fbf9716bac8828e60c265db8b5e5c1c2116ba1e30de2e694
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
