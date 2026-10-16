#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/aarch64-cross.ini (service: None, risk: medium)
# staged source: shell/nuxel-shell/aarch64-cross.ini
# previous-hash: 28146a932693b8775e3a3f26fc867f523bfc91933c3233e65c6307eb904a1fb5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/aarch64-cross.ini.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/aarch64-cross.ini.nuxel-rollback /usr/lib/nuxel/src/shell/aarch64-cross.ini; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/aarch64-cross.ini ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/aarch64-cross.ini | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/aarch64-cross.ini)"
if [ -e /usr/lib/nuxel/src/shell/aarch64-cross.ini ] && [ ! -e /usr/lib/nuxel/src/shell/aarch64-cross.ini.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/aarch64-cross.ini /usr/lib/nuxel/src/shell/aarch64-cross.ini.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/aarch64-cross.ini.nuxel-staged
printf '%s  %s\n' 28146a932693b8775e3a3f26fc867f523bfc91933c3233e65c6307eb904a1fb5 /usr/lib/nuxel/src/shell/aarch64-cross.ini.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/aarch64-cross.ini.nuxel-staged /usr/lib/nuxel/src/shell/aarch64-cross.ini
sha256sum /usr/lib/nuxel/src/shell/aarch64-cross.ini | grep -q 28146a932693b8775e3a3f26fc867f523bfc91933c3233e65c6307eb904a1fb5
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
