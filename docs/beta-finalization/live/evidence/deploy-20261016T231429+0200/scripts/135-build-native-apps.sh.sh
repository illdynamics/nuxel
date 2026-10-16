#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/build-native-apps.sh (service: None, risk: medium)
# staged source: shell/nuxel-shell/build-native-apps.sh
# previous-hash: 5df84cb8c9c053963596b48a50ef2494e494dca1c7faa6813a0aa571c89e3d92
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-rollback /usr/lib/nuxel/src/shell/build-native-apps.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/build-native-apps.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/build-native-apps.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/build-native-apps.sh)"
if [ -e /usr/lib/nuxel/src/shell/build-native-apps.sh ] && [ ! -e /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/build-native-apps.sh /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-staged
printf '%s  %s\n' 5df84cb8c9c053963596b48a50ef2494e494dca1c7faa6813a0aa571c89e3d92 /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/build-native-apps.sh.nuxel-staged /usr/lib/nuxel/src/shell/build-native-apps.sh
sha256sum /usr/lib/nuxel/src/shell/build-native-apps.sh | grep -q 5df84cb8c9c053963596b48a50ef2494e494dca1c7faa6813a0aa571c89e3d92
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
