#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/gnss/gnss.json (service: None, risk: medium)
# staged source: configs/nuxel/gnss/gnss.json
# previous-hash: efe9921cfe300e79c86fb444681354e02707fd3242b09f319e38bc79f9e5efb0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/gnss/gnss.json.nuxel-rollback ]; then cp -a /etc/nuxel/gnss/gnss.json.nuxel-rollback /etc/nuxel/gnss/gnss.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/gnss/gnss.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/gnss/gnss.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/gnss/gnss.json)"
if [ -e /etc/nuxel/gnss/gnss.json ] && [ ! -e /etc/nuxel/gnss/gnss.json.nuxel-rollback ]; then cp -a /etc/nuxel/gnss/gnss.json /etc/nuxel/gnss/gnss.json.nuxel-rollback; fi
test -f /etc/nuxel/gnss/gnss.json.nuxel-staged
printf '%s  %s\n' efe9921cfe300e79c86fb444681354e02707fd3242b09f319e38bc79f9e5efb0 /etc/nuxel/gnss/gnss.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/gnss/gnss.json.nuxel-staged /etc/nuxel/gnss/gnss.json
sha256sum /etc/nuxel/gnss/gnss.json | grep -q efe9921cfe300e79c86fb444681354e02707fd3242b09f319e38bc79f9e5efb0
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
