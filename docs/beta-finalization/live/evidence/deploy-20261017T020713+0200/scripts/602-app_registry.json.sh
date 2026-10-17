#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/app_registry.json
# previous-hash: 11cc731bd1c3ad45e82eccb0733f7f34e41cb6a42bd06b857f6161cf48f533ee
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-staged
printf '%s  %s\n' 11cc731bd1c3ad45e82eccb0733f7f34e41cb6a42bd06b857f6161cf48f533ee /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json | grep -q 11cc731bd1c3ad45e82eccb0733f7f34e41cb6a42bd06b857f6161cf48f533ee
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
