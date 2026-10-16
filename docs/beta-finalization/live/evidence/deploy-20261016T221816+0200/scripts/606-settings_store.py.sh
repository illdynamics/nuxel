#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/settings_store.py
# previous-hash: bf3e123b7332e839fbf9716bac8828e60c265db8b5e5c1c2116ba1e30de2e694
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-staged
printf '%s  %s\n' bf3e123b7332e839fbf9716bac8828e60c265db8b5e5c1c2116ba1e30de2e694 /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py | grep -q bf3e123b7332e839fbf9716bac8828e60c265db8b5e5c1c2116ba1e30de2e694
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/settings_store.py; true; fi
