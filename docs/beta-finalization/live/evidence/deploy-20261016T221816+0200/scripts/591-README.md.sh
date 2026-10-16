#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/README.md (service: None, risk: medium)
# staged source: shell/nuxel-home-native/README.md
# previous-hash: 4be874102f1095e1b39d48d67dd5fc59261875624d801be7ba4b038ffe5efcf3
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/README.md)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/README.md ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/README.md /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-staged
printf '%s  %s\n' 4be874102f1095e1b39d48d67dd5fc59261875624d801be7ba4b038ffe5efcf3 /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/README.md
sha256sum /usr/share/nuxel/shell/nuxel-home-native/README.md | grep -q 4be874102f1095e1b39d48d67dd5fc59261875624d801be7ba4b038ffe5efcf3
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/README.md.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/README.md; true; fi
