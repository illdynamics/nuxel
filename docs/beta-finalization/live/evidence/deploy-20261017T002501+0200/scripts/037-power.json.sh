#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/power/power.json (service: None, risk: medium)
# staged source: configs/nuxel/power/power.json
# previous-hash: 23a9dfedaf1c3f61ce11b2843e4533382161fa10caf00bfa616a4755a733c0a0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/power/power.json.nuxel-rollback ]; then cp -a /etc/nuxel/power/power.json.nuxel-rollback /etc/nuxel/power/power.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/power/power.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/power/power.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/power/power.json)"
if [ -e /etc/nuxel/power/power.json ] && [ ! -e /etc/nuxel/power/power.json.nuxel-rollback ]; then cp -a /etc/nuxel/power/power.json /etc/nuxel/power/power.json.nuxel-rollback; fi
test -f /etc/nuxel/power/power.json.nuxel-staged
printf '%s  %s\n' 23a9dfedaf1c3f61ce11b2843e4533382161fa10caf00bfa616a4755a733c0a0 /etc/nuxel/power/power.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/power/power.json.nuxel-staged /etc/nuxel/power/power.json
sha256sum /etc/nuxel/power/power.json | grep -q 23a9dfedaf1c3f61ce11b2843e4533382161fa10caf00bfa616a4755a733c0a0
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
