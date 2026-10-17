#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/sandbox.h
# previous-hash: 68abb245a5760270d798f8cea9882b0fe6c7aa3a6d16a3c0697c20adc6e69399
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-staged
printf '%s  %s\n' 68abb245a5760270d798f8cea9882b0fe6c7aa3a6d16a3c0697c20adc6e69399 /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h
sha256sum /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h | grep -q 68abb245a5760270d798f8cea9882b0fe6c7aa3a6d16a3c0697c20adc6e69399
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
