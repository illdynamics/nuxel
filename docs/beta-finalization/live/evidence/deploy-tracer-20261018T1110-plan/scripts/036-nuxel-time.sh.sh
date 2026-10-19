#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-time.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-time.sh
# previous-hash: 15acea3964bbef454c3c07604645a6dba453fb0d683626ace42b0ac488aa3175
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-time.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-time.sh.nuxel-rollback /usr/local/bin/nuxel-time.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-time.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-time.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-time.sh)"
if [ -e /usr/local/bin/nuxel-time.sh ] && [ ! -e /usr/local/bin/nuxel-time.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-time.sh /usr/local/bin/nuxel-time.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-time.sh.nuxel-staged
printf '%s  %s\n' 15acea3964bbef454c3c07604645a6dba453fb0d683626ace42b0ac488aa3175 /usr/local/bin/nuxel-time.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-time.sh.nuxel-staged /usr/local/bin/nuxel-time.sh
sha256sum /usr/local/bin/nuxel-time.sh | grep -q 15acea3964bbef454c3c07604645a6dba453fb0d683626ace42b0ac488aa3175
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
