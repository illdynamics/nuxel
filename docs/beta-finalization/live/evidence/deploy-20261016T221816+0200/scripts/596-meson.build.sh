#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/meson.build (service: None, risk: medium)
# staged source: shell/nuxel-home-native/meson.build
# previous-hash: 23968e0f2192324065d43e8c6d9eaa51b133d4b43145e9405158033fc449e6ce
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/meson.build)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/meson.build ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/meson.build /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-staged
printf '%s  %s\n' 23968e0f2192324065d43e8c6d9eaa51b133d4b43145e9405158033fc449e6ce /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/meson.build
sha256sum /usr/share/nuxel/shell/nuxel-home-native/meson.build | grep -q 23968e0f2192324065d43e8c6d9eaa51b133d4b43145e9405158033fc449e6ce
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/meson.build; true; fi
