#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/bluetooth/bluetooth.json (service: None, risk: medium)
# staged source: configs/nuxel/bluetooth/bluetooth.json
# previous-hash: a6db6e9effc0e23e1cbd92bbaaf0afae4b16baff844319f209cc96b72b723f7c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/bluetooth/bluetooth.json.nuxel-rollback ]; then cp -a /etc/nuxel/bluetooth/bluetooth.json.nuxel-rollback /etc/nuxel/bluetooth/bluetooth.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/bluetooth/bluetooth.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/bluetooth/bluetooth.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/bluetooth/bluetooth.json)"
if [ -e /etc/nuxel/bluetooth/bluetooth.json ] && [ ! -e /etc/nuxel/bluetooth/bluetooth.json.nuxel-rollback ]; then cp -a /etc/nuxel/bluetooth/bluetooth.json /etc/nuxel/bluetooth/bluetooth.json.nuxel-rollback; fi
test -f /etc/nuxel/bluetooth/bluetooth.json.nuxel-staged
printf '%s  %s\n' a6db6e9effc0e23e1cbd92bbaaf0afae4b16baff844319f209cc96b72b723f7c /etc/nuxel/bluetooth/bluetooth.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bluetooth/bluetooth.json.nuxel-staged /etc/nuxel/bluetooth/bluetooth.json
sha256sum /etc/nuxel/bluetooth/bluetooth.json | grep -q a6db6e9effc0e23e1cbd92bbaaf0afae4b16baff844319f209cc96b72b723f7c
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
