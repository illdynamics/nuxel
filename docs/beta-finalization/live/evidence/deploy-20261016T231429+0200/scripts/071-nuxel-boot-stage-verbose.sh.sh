#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-boot-stage-verbose.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-boot-stage-verbose.sh
# previous-hash: 889cb30eafd223f2c2f9291934202e123db6ef7173e1b6d53f8c071b07202e50
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-boot-stage-verbose.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-boot-stage-verbose.sh.nuxel-rollback /usr/local/bin/nuxel-boot-stage-verbose.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-boot-stage-verbose.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-boot-stage-verbose.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-boot-stage-verbose.sh)"
if [ -e /usr/local/bin/nuxel-boot-stage-verbose.sh ] && [ ! -e /usr/local/bin/nuxel-boot-stage-verbose.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-boot-stage-verbose.sh /usr/local/bin/nuxel-boot-stage-verbose.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-boot-stage-verbose.sh.nuxel-staged
printf '%s  %s\n' 889cb30eafd223f2c2f9291934202e123db6ef7173e1b6d53f8c071b07202e50 /usr/local/bin/nuxel-boot-stage-verbose.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-boot-stage-verbose.sh.nuxel-staged /usr/local/bin/nuxel-boot-stage-verbose.sh
sha256sum /usr/local/bin/nuxel-boot-stage-verbose.sh | grep -q 889cb30eafd223f2c2f9291934202e123db6ef7173e1b6d53f8c071b07202e50
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
