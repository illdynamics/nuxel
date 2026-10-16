#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-phone-data/nuxel-phone-data.h
# previous-hash: 633b11789ac5a29cd0b4bf1741b3c9d1ad904740d96dd6ca939798c174d61c62
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h.nuxel-staged
printf '%s  %s\n' 633b11789ac5a29cd0b4bf1741b3c9d1ad904740d96dd6ca939798c174d61c62 /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h
sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h | grep -q 633b11789ac5a29cd0b4bf1741b3c9d1ad904740d96dd6ca939798c174d61c62
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.h; true; fi
