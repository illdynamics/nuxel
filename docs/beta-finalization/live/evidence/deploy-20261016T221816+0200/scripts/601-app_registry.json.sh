#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/app_registry.json
# previous-hash: 11cc731bd1c3ad45e82eccb0733f7f34e41cb6a42bd06b857f6161cf48f533ee
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-staged
printf '%s  %s\n' 11cc731bd1c3ad45e82eccb0733f7f34e41cb6a42bd06b857f6161cf48f533ee /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json | grep -q 11cc731bd1c3ad45e82eccb0733f7f34e41cb6a42bd06b857f6161cf48f533ee
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json; true; fi
