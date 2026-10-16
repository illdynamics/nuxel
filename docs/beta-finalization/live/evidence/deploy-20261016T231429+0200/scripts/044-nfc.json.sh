#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/nfc/nfc.json (service: None, risk: medium)
# staged source: configs/nuxel/nfc/nfc.json
# previous-hash: 1f84eaf6dc911c538d9f73df54989bae2ce20c7126ae07ba9f4a9b6e89172757
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/nfc/nfc.json.nuxel-rollback ]; then cp -a /etc/nuxel/nfc/nfc.json.nuxel-rollback /etc/nuxel/nfc/nfc.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/nfc/nfc.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/nfc/nfc.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/nfc/nfc.json)"
if [ -e /etc/nuxel/nfc/nfc.json ] && [ ! -e /etc/nuxel/nfc/nfc.json.nuxel-rollback ]; then cp -a /etc/nuxel/nfc/nfc.json /etc/nuxel/nfc/nfc.json.nuxel-rollback; fi
test -f /etc/nuxel/nfc/nfc.json.nuxel-staged
printf '%s  %s\n' 1f84eaf6dc911c538d9f73df54989bae2ce20c7126ae07ba9f4a9b6e89172757 /etc/nuxel/nfc/nfc.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/nfc/nfc.json.nuxel-staged /etc/nuxel/nfc/nfc.json
sha256sum /etc/nuxel/nfc/nfc.json | grep -q 1f84eaf6dc911c538d9f73df54989bae2ce20c7126ae07ba9f4a9b6e89172757
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
