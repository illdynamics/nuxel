#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/README.md (service: None, risk: medium)
# staged source: tools/s10plus/a33/README.md
# previous-hash: 2160719a9f26aebace6135056b028d1c873eac0044d6977db368c35bbd09678a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/README.md.nuxel-rollback /usr/lib/nuxel/src/a33/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/README.md)"
if [ -e /usr/lib/nuxel/src/a33/README.md ] && [ ! -e /usr/lib/nuxel/src/a33/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/README.md /usr/lib/nuxel/src/a33/README.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/README.md.nuxel-staged
printf '%s  %s\n' 2160719a9f26aebace6135056b028d1c873eac0044d6977db368c35bbd09678a /usr/lib/nuxel/src/a33/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/README.md.nuxel-staged /usr/lib/nuxel/src/a33/README.md
sha256sum /usr/lib/nuxel/src/a33/README.md | grep -q 2160719a9f26aebace6135056b028d1c873eac0044d6977db368c35bbd09678a
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
