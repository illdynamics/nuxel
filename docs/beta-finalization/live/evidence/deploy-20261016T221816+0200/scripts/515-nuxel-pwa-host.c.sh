#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-pwa-host.c (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-pwa-host.c
# previous-hash: 15c27e9ed6ed6600e924cdd7c5ffbf93c2e53b6883e60042b157845d78b09f2c
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-pwa-host.c)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-pwa-host.c ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-pwa-host.c /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-staged
printf '%s  %s\n' 15c27e9ed6ed6600e924cdd7c5ffbf93c2e53b6883e60042b157845d78b09f2c /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-pwa-host.c
sha256sum /usr/lib/nuxel/src/a33/nuxel-pwa-host.c | grep -q 15c27e9ed6ed6600e924cdd7c5ffbf93c2e53b6883e60042b157845d78b09f2c
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-pwa-host.c; true; fi
