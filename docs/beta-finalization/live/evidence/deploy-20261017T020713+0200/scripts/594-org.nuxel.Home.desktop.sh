#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop (service: None, risk: medium)
# staged source: shell/nuxel-home-native/data/org.nuxel.Home.desktop
# previous-hash: 890c5d61743aa63bb8d7cd9343ed3f2c25f2530fb0947a90599e9548f63f95a4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop.nuxel-staged
printf '%s  %s\n' 890c5d61743aa63bb8d7cd9343ed3f2c25f2530fb0947a90599e9548f63f95a4 /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop
sha256sum /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.desktop | grep -q 890c5d61743aa63bb8d7cd9343ed3f2c25f2530fb0947a90599e9548f63f95a4
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
