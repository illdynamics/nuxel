#!/bin/sh
# first-party capability grants and hardware config documents -> /etc/nuxel/gnss/gnss.json (service: nuxel-bridge, risk: medium)
# staged source: configs/nuxel/gnss/gnss.json
# previous-hash: f7286633090abe321c9d50d48d1eb04299a6a59c947e391f3b21bf8d0ab6c61b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/gnss/gnss.json.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /etc/nuxel/gnss/gnss.json.nuxel-rollback.pre-deploy-20261027T181522-2198480 /etc/nuxel/gnss/gnss.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -d /var/lib/nuxel/permissions
if [ -e /etc/nuxel/gnss/gnss.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/gnss/gnss.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/gnss/gnss.json)"
if [ -e /etc/nuxel/gnss/gnss.json ] && [ ! -e /etc/nuxel/gnss/gnss.json.nuxel-rollback ]; then cp -a /etc/nuxel/gnss/gnss.json /etc/nuxel/gnss/gnss.json.nuxel-rollback; fi
if [ -e /etc/nuxel/gnss/gnss.json ] && [ ! -e /etc/nuxel/gnss/gnss.json.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /etc/nuxel/gnss/gnss.json /etc/nuxel/gnss/gnss.json.nuxel-rollback.pre-deploy-20261027T181522-2198480; fi
test -f /etc/nuxel/gnss/gnss.json.nuxel-staged
printf '%s  %s\n' f7286633090abe321c9d50d48d1eb04299a6a59c947e391f3b21bf8d0ab6c61b /etc/nuxel/gnss/gnss.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/gnss/gnss.json.nuxel-staged /etc/nuxel/gnss/gnss.json
sha256sum /etc/nuxel/gnss/gnss.json | grep -q f7286633090abe321c9d50d48d1eb04299a6a59c947e391f3b21bf8d0ab6c61b
echo INSTALL-OK
