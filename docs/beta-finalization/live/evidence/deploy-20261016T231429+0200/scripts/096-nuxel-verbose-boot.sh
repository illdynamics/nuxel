#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/libexec/nuxel/nuxel-verbose-boot (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-verbose-boot.py
# previous-hash: b484b5750216a1a3eb311e3e01305678e2ba3aeb774888c7aad62d17a784cc49
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/libexec/nuxel/nuxel-verbose-boot.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-verbose-boot.nuxel-rollback /usr/libexec/nuxel/nuxel-verbose-boot; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/libexec/nuxel/nuxel-verbose-boot ]; then printf 'PREV=%s\n' "$(sha256sum /usr/libexec/nuxel/nuxel-verbose-boot | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/libexec/nuxel/nuxel-verbose-boot)"
if [ -e /usr/libexec/nuxel/nuxel-verbose-boot ] && [ ! -e /usr/libexec/nuxel/nuxel-verbose-boot.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-verbose-boot /usr/libexec/nuxel/nuxel-verbose-boot.nuxel-rollback; fi
test -f /usr/libexec/nuxel/nuxel-verbose-boot.nuxel-staged
printf '%s  %s\n' b484b5750216a1a3eb311e3e01305678e2ba3aeb774888c7aad62d17a784cc49 /usr/libexec/nuxel/nuxel-verbose-boot.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/libexec/nuxel/nuxel-verbose-boot.nuxel-staged /usr/libexec/nuxel/nuxel-verbose-boot
sha256sum /usr/libexec/nuxel/nuxel-verbose-boot | grep -q b484b5750216a1a3eb311e3e01305678e2ba3aeb774888c7aad62d17a784cc49
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
