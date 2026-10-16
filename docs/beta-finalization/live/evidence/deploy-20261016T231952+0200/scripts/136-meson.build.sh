#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/meson.build (service: None, risk: medium)
# staged source: shell/nuxel-shell/meson.build
# previous-hash: 8a70a4fb6aa05146350ed2447f80fbef2668aeea1aac40a9168cb3e796880677
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/meson.build.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/meson.build.nuxel-rollback /usr/lib/nuxel/src/shell/meson.build; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/meson.build ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/meson.build | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/meson.build)"
if [ -e /usr/lib/nuxel/src/shell/meson.build ] && [ ! -e /usr/lib/nuxel/src/shell/meson.build.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/meson.build /usr/lib/nuxel/src/shell/meson.build.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/meson.build.nuxel-staged
printf '%s  %s\n' 8a70a4fb6aa05146350ed2447f80fbef2668aeea1aac40a9168cb3e796880677 /usr/lib/nuxel/src/shell/meson.build.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/meson.build.nuxel-staged /usr/lib/nuxel/src/shell/meson.build
sha256sum /usr/lib/nuxel/src/shell/meson.build | grep -q 8a70a4fb6aa05146350ed2447f80fbef2668aeea1aac40a9168cb3e796880677
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
