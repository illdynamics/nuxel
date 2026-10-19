#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/libexec/nuxel/nuxel-provision-services.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-provision-services.sh
# previous-hash: bd223c214547b6509e81a276eebfdcf7501ec05b463237c714d06b8a21464fb3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/libexec/nuxel/nuxel-provision-services.sh.nuxel-rollback ]; then cp -a /usr/local/libexec/nuxel/nuxel-provision-services.sh.nuxel-rollback /usr/local/libexec/nuxel/nuxel-provision-services.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/libexec/nuxel/nuxel-provision-services.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/libexec/nuxel/nuxel-provision-services.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/libexec/nuxel/nuxel-provision-services.sh)"
if [ -e /usr/local/libexec/nuxel/nuxel-provision-services.sh ] && [ ! -e /usr/local/libexec/nuxel/nuxel-provision-services.sh.nuxel-rollback ]; then cp -a /usr/local/libexec/nuxel/nuxel-provision-services.sh /usr/local/libexec/nuxel/nuxel-provision-services.sh.nuxel-rollback; fi
test -f /usr/local/libexec/nuxel/nuxel-provision-services.sh.nuxel-staged
printf '%s  %s\n' bd223c214547b6509e81a276eebfdcf7501ec05b463237c714d06b8a21464fb3 /usr/local/libexec/nuxel/nuxel-provision-services.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/libexec/nuxel/nuxel-provision-services.sh.nuxel-staged /usr/local/libexec/nuxel/nuxel-provision-services.sh
sha256sum /usr/local/libexec/nuxel/nuxel-provision-services.sh | grep -q bd223c214547b6509e81a276eebfdcf7501ec05b463237c714d06b8a21464fb3
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
