#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg (service: None, risk: medium)
# staged source: shell/nuxel-home-native/data/icons/org.nuxel.Home.svg
# previous-hash: 30fd184fa99a4cf661c9ffa892c89deb22fb5dc18c9f841c46b83622093aded0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg.nuxel-staged
printf '%s  %s\n' 30fd184fa99a4cf661c9ffa892c89deb22fb5dc18c9f841c46b83622093aded0 /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg
sha256sum /usr/share/nuxel/shell/nuxel-home-native/data/icons/org.nuxel.Home.svg | grep -q 30fd184fa99a4cf661c9ffa892c89deb22fb5dc18c9f841c46b83622093aded0
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
