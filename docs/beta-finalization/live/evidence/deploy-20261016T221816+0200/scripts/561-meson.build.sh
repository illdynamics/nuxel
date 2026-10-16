#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/meson.build (service: None, risk: medium)
# staged source: shell/nuxel-shell/meson.build
# previous-hash: 8a70a4fb6aa05146350ed2447f80fbef2668aeea1aac40a9168cb3e796880677
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/meson.build)"
if [ -e /usr/lib/nuxel/src/shell/meson.build ]; then cp -a /usr/lib/nuxel/src/shell/meson.build /usr/lib/nuxel/src/shell/meson.build.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/meson.build.nuxel-staged
printf '%s  %s\n' 8a70a4fb6aa05146350ed2447f80fbef2668aeea1aac40a9168cb3e796880677 /usr/lib/nuxel/src/shell/meson.build.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/meson.build.nuxel-staged /usr/lib/nuxel/src/shell/meson.build
sha256sum /usr/lib/nuxel/src/shell/meson.build | grep -q 8a70a4fb6aa05146350ed2447f80fbef2668aeea1aac40a9168cb3e796880677
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/meson.build.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/meson.build.nuxel-rollback /usr/lib/nuxel/src/shell/meson.build; true; fi
