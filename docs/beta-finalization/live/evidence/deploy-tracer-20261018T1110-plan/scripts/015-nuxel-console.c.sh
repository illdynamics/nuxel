#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-console.c (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-console.c
# previous-hash: 8d1a56715ce915a72ac08ad2293d2b53d44172bdd48b58e560f27d3845ca7db4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-console.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/nuxel-console.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/nuxel-console.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-console.c)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-console.c ] && [ ! -e /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-console.c /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-staged
printf '%s  %s\n' 8d1a56715ce915a72ac08ad2293d2b53d44172bdd48b58e560f27d3845ca7db4 /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-console.c.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-console.c
sha256sum /usr/lib/nuxel/src/a33/nuxel-console.c | grep -q 8d1a56715ce915a72ac08ad2293d2b53d44172bdd48b58e560f27d3845ca7db4
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
