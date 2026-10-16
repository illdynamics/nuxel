#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/sandbox.h
# previous-hash: 68abb245a5760270d798f8cea9882b0fe6c7aa3a6d16a3c0697c20adc6e69399
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-staged
printf '%s  %s\n' 68abb245a5760270d798f8cea9882b0fe6c7aa3a6d16a3c0697c20adc6e69399 /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h
sha256sum /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h | grep -q 68abb245a5760270d798f8cea9882b0fe6c7aa3a6d16a3c0697c20adc6e69399
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.h; true; fi
