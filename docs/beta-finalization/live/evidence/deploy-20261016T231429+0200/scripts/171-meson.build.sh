#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/meson.build (service: None, risk: medium)
# staged source: shell/nuxel-home-native/meson.build
# previous-hash: 23968e0f2192324065d43e8c6d9eaa51b133d4b43145e9405158033fc449e6ce
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/meson.build; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/meson.build ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/meson.build | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/meson.build)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/meson.build ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/meson.build /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-staged
printf '%s  %s\n' 23968e0f2192324065d43e8c6d9eaa51b133d4b43145e9405158033fc449e6ce /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/meson.build.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/meson.build
sha256sum /usr/share/nuxel/shell/nuxel-home-native/meson.build | grep -q 23968e0f2192324065d43e8c6d9eaa51b133d4b43145e9405158033fc449e6ce
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
