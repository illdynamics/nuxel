#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-console.c (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-console.c
# previous-hash: 8d1a56715ce915a72ac08ad2293d2b53d44172bdd48b58e560f27d3845ca7db4
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-console.c)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-console.c ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-console.c /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-staged
printf '%s  %s\n' 8d1a56715ce915a72ac08ad2293d2b53d44172bdd48b58e560f27d3845ca7db4 /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-console.c
sha256sum /usr/lib/nuxel/src/a33/nuxel-console.c | grep -q 8d1a56715ce915a72ac08ad2293d2b53d44172bdd48b58e560f27d3845ca7db4
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-console.c; true; fi
