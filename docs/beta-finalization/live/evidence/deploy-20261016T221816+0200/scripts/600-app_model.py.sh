#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/app_model.py
# previous-hash: 587c3111581ce5ef11507a0cf58a4d844dea43223bb30750f796bbaa9e2a9392
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-staged
printf '%s  %s\n' 587c3111581ce5ef11507a0cf58a4d844dea43223bb30750f796bbaa9e2a9392 /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py | grep -q 587c3111581ce5ef11507a0cf58a4d844dea43223bb30750f796bbaa9e2a9392
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_model.py; true; fi
