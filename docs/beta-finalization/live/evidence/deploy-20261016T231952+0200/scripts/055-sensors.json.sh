#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/sensors/sensors.json (service: None, risk: medium)
# staged source: configs/nuxel/sensors/sensors.json
# previous-hash: e8a904460ec7fdc3af4c330d6782432bb70d894d3f84df54c766ebb28981fc40
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sensors/sensors.json.nuxel-rollback ]; then cp -a /etc/nuxel/sensors/sensors.json.nuxel-rollback /etc/nuxel/sensors/sensors.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sensors/sensors.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sensors/sensors.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sensors/sensors.json)"
if [ -e /etc/nuxel/sensors/sensors.json ] && [ ! -e /etc/nuxel/sensors/sensors.json.nuxel-rollback ]; then cp -a /etc/nuxel/sensors/sensors.json /etc/nuxel/sensors/sensors.json.nuxel-rollback; fi
test -f /etc/nuxel/sensors/sensors.json.nuxel-staged
printf '%s  %s\n' e8a904460ec7fdc3af4c330d6782432bb70d894d3f84df54c766ebb28981fc40 /etc/nuxel/sensors/sensors.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sensors/sensors.json.nuxel-staged /etc/nuxel/sensors/sensors.json
sha256sum /etc/nuxel/sensors/sensors.json | grep -q e8a904460ec7fdc3af4c330d6782432bb70d894d3f84df54c766ebb28981fc40
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
