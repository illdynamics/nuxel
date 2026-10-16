#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/build-a33-boot.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/build-a33-boot.sh
# previous-hash: 84e005ffc9bb9350e83733077ead80a9cdb75e0171dd3b32795ce72cfd350a98
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/build-a33-boot.sh.nuxel-rollback ]; then cp -a /usr/local/bin/build-a33-boot.sh.nuxel-rollback /usr/local/bin/build-a33-boot.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/build-a33-boot.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/build-a33-boot.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/build-a33-boot.sh)"
if [ -e /usr/local/bin/build-a33-boot.sh ] && [ ! -e /usr/local/bin/build-a33-boot.sh.nuxel-rollback ]; then cp -a /usr/local/bin/build-a33-boot.sh /usr/local/bin/build-a33-boot.sh.nuxel-rollback; fi
test -f /usr/local/bin/build-a33-boot.sh.nuxel-staged
printf '%s  %s\n' 84e005ffc9bb9350e83733077ead80a9cdb75e0171dd3b32795ce72cfd350a98 /usr/local/bin/build-a33-boot.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/build-a33-boot.sh.nuxel-staged /usr/local/bin/build-a33-boot.sh
sha256sum /usr/local/bin/build-a33-boot.sh | grep -q 84e005ffc9bb9350e83733077ead80a9cdb75e0171dd3b32795ce72cfd350a98
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
