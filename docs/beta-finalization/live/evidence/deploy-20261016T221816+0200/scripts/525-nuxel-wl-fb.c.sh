#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-wl-fb.c (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-wl-fb.c
# previous-hash: 052bfdbf673ef658c93b8c07925f2c9249af3c755a011ccbe90011c616f7b768
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-wl-fb.c)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-wl-fb.c ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-wl-fb.c /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-staged
printf '%s  %s\n' 052bfdbf673ef658c93b8c07925f2c9249af3c755a011ccbe90011c616f7b768 /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-wl-fb.c
sha256sum /usr/lib/nuxel/src/a33/nuxel-wl-fb.c | grep -q 052bfdbf673ef658c93b8c07925f2c9249af3c755a011ccbe90011c616f7b768
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-wl-fb.c; true; fi
