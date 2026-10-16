#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/build-native-apps.sh (service: None, risk: medium)
# staged source: shell/nuxel-shell/build-native-apps.sh
# previous-hash: 5df84cb8c9c053963596b48a50ef2494e494dca1c7faa6813a0aa571c89e3d92
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/build-native-apps.sh)"
if [ -e /usr/lib/nuxel/src/shell/build-native-apps.sh ]; then cp -a /usr/lib/nuxel/src/shell/build-native-apps.sh /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-staged
printf '%s  %s\n' 5df84cb8c9c053963596b48a50ef2494e494dca1c7faa6813a0aa571c89e3d92 /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-staged /usr/lib/nuxel/src/shell/build-native-apps.sh
sha256sum /usr/lib/nuxel/src/shell/build-native-apps.sh | grep -q 5df84cb8c9c053963596b48a50ef2494e494dca1c7faa6813a0aa571c89e3d92
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-rollback /usr/lib/nuxel/src/shell/build-native-apps.sh; true; fi
