#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel_home/style.css
# previous-hash: b036194d56b226d5b1ecf4ea6718efb33e2791251cd166f8a1e869fe0f90a161
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css.nuxel-staged
printf '%s  %s\n' b036194d56b226d5b1ecf4ea6718efb33e2791251cd166f8a1e869fe0f90a161 /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/style.css | grep -q b036194d56b226d5b1ecf4ea6718efb33e2791251cd166f8a1e869fe0f90a161
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
