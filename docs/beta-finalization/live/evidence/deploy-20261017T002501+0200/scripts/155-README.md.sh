#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/README.md (service: None, risk: medium)
# staged source: shell/nuxel-home-native/README.md
# previous-hash: 4be874102f1095e1b39d48d67dd5fc59261875624d801be7ba4b038ffe5efcf3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/README.md)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/README.md ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/README.md /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-staged
printf '%s  %s\n' 4be874102f1095e1b39d48d67dd5fc59261875624d801be7ba4b038ffe5efcf3 /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/README.md
sha256sum /usr/share/nuxel/shell/nuxel-home-native/README.md | grep -q 4be874102f1095e1b39d48d67dd5fc59261875624d801be7ba4b038ffe5efcf3
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
