#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/security/privacy-config.json (service: None, risk: medium)
# staged source: configs/nuxel/security/privacy-config.json
# previous-hash: 3815679ac18fa5a0cc5fb2789c46657acf161c96bcfd62b7cbec7b5bc5d33ec7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/security/privacy-config.json.nuxel-rollback ]; then cp -a /etc/nuxel/security/privacy-config.json.nuxel-rollback /etc/nuxel/security/privacy-config.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/security/privacy-config.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/security/privacy-config.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/security/privacy-config.json)"
if [ -e /etc/nuxel/security/privacy-config.json ] && [ ! -e /etc/nuxel/security/privacy-config.json.nuxel-rollback ]; then cp -a /etc/nuxel/security/privacy-config.json /etc/nuxel/security/privacy-config.json.nuxel-rollback; fi
test -f /etc/nuxel/security/privacy-config.json.nuxel-staged
printf '%s  %s\n' 3815679ac18fa5a0cc5fb2789c46657acf161c96bcfd62b7cbec7b5bc5d33ec7 /etc/nuxel/security/privacy-config.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/security/privacy-config.json.nuxel-staged /etc/nuxel/security/privacy-config.json
sha256sum /etc/nuxel/security/privacy-config.json | grep -q 3815679ac18fa5a0cc5fb2789c46657acf161c96bcfd62b7cbec7b5bc5d33ec7
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
