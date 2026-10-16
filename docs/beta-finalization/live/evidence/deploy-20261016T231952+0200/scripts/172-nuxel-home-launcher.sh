#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher (service: None, risk: medium)
# staged source: shell/nuxel-home-native/nuxel-home-launcher
# previous-hash: 4260e9c8614c44285e0f3a73bcf432e286668b69eb86c6553257790f6b721e91
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher.nuxel-staged
printf '%s  %s\n' 4260e9c8614c44285e0f3a73bcf432e286668b69eb86c6553257790f6b721e91 /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher
sha256sum /usr/share/nuxel/shell/nuxel-home-native/nuxel-home-launcher | grep -q 4260e9c8614c44285e0f3a73bcf432e286668b69eb86c6553257790f6b721e91
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
