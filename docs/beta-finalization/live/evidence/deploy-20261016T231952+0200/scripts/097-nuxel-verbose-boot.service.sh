#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /etc/systemd/system/nuxel-verbose-boot.service (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-verbose-boot.service
# previous-hash: ddbffc025ebdb7982cd80501df403e88d8ac3823fa140806fcb694d0a364c461
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-verbose-boot.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-verbose-boot.service.nuxel-rollback /etc/systemd/system/nuxel-verbose-boot.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-verbose-boot.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-verbose-boot.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-verbose-boot.service)"
if [ -e /etc/systemd/system/nuxel-verbose-boot.service ] && [ ! -e /etc/systemd/system/nuxel-verbose-boot.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-verbose-boot.service /etc/systemd/system/nuxel-verbose-boot.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-verbose-boot.service.nuxel-staged
printf '%s  %s\n' ddbffc025ebdb7982cd80501df403e88d8ac3823fa140806fcb694d0a364c461 /etc/systemd/system/nuxel-verbose-boot.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-verbose-boot.service.nuxel-staged /etc/systemd/system/nuxel-verbose-boot.service
sha256sum /etc/systemd/system/nuxel-verbose-boot.service | grep -q ddbffc025ebdb7982cd80501df403e88d8ac3823fa140806fcb694d0a364c461
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
