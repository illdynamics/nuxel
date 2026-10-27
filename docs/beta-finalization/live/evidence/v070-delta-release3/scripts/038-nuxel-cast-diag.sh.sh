#!/bin/sh
# Typecast and Type-C diagnostics -> /usr/local/bin/nuxel-cast-diag.sh (service: None, risk: low)
# staged source: tools/s10plus/a33/nuxel-cast-diag.sh
# previous-hash: d2516a57150576a992d870709824ca34d91a4b2b70d5c68e58eb805f562910b8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-cast-diag.sh.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/local/bin/nuxel-cast-diag.sh.nuxel-rollback.pre-v070-delta-release3 /usr/local/bin/nuxel-cast-diag.sh; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/local/bin/nuxel-cast-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-cast-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-cast-diag.sh)"
if [ -e /usr/local/bin/nuxel-cast-diag.sh ] && [ ! -e /usr/local/bin/nuxel-cast-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-cast-diag.sh /usr/local/bin/nuxel-cast-diag.sh.nuxel-rollback; fi
if [ -e /usr/local/bin/nuxel-cast-diag.sh ] && [ ! -e /usr/local/bin/nuxel-cast-diag.sh.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/local/bin/nuxel-cast-diag.sh /usr/local/bin/nuxel-cast-diag.sh.nuxel-rollback.pre-v070-delta-release3; fi
test -f /usr/local/bin/nuxel-cast-diag.sh.nuxel-staged
printf '%s  %s\n' d2516a57150576a992d870709824ca34d91a4b2b70d5c68e58eb805f562910b8 /usr/local/bin/nuxel-cast-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-cast-diag.sh.nuxel-staged /usr/local/bin/nuxel-cast-diag.sh
sha256sum /usr/local/bin/nuxel-cast-diag.sh | grep -q d2516a57150576a992d870709824ca34d91a4b2b70d5c68e58eb805f562910b8
echo INSTALL-OK
