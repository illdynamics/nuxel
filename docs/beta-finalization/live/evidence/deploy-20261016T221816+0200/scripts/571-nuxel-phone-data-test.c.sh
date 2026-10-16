#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-phone-data/nuxel-phone-data-test.c
# previous-hash: 2f9bb1f17b61e866d142f16e33518b3446d8e5c38d8b752422b71048864aeb71
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c.nuxel-staged
printf '%s  %s\n' 2f9bb1f17b61e866d142f16e33518b3446d8e5c38d8b752422b71048864aeb71 /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c | grep -q 2f9bb1f17b61e866d142f16e33518b3446d8e5c38d8b752422b71048864aeb71
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data-test.c; true; fi
