#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/time/time.json (service: None, risk: medium)
# staged source: configs/nuxel/time/time.json
# previous-hash: 459ff99a711e62cd0b40923947b4aecc71213216628208c02aeff6b4eed80da4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/time/time.json.nuxel-rollback ]; then cp -a /etc/nuxel/time/time.json.nuxel-rollback /etc/nuxel/time/time.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/time/time.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/time/time.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/time/time.json)"
if [ -e /etc/nuxel/time/time.json ] && [ ! -e /etc/nuxel/time/time.json.nuxel-rollback ]; then cp -a /etc/nuxel/time/time.json /etc/nuxel/time/time.json.nuxel-rollback; fi
test -f /etc/nuxel/time/time.json.nuxel-staged
printf '%s  %s\n' 459ff99a711e62cd0b40923947b4aecc71213216628208c02aeff6b4eed80da4 /etc/nuxel/time/time.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/time/time.json.nuxel-staged /etc/nuxel/time/time.json
sha256sum /etc/nuxel/time/time.json | grep -q 459ff99a711e62cd0b40923947b4aecc71213216628208c02aeff6b4eed80da4
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
