#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/capabilities/hardware-subsystems.json (service: None, risk: medium)
# staged source: configs/nuxel/capabilities/hardware-subsystems.json
# previous-hash: 806d076770519c57bead9090e00f5e6c6d05787956494f4d31c115fb91c920f8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/capabilities/hardware-subsystems.json.nuxel-rollback ]; then cp -a /etc/nuxel/capabilities/hardware-subsystems.json.nuxel-rollback /etc/nuxel/capabilities/hardware-subsystems.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/capabilities/hardware-subsystems.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/capabilities/hardware-subsystems.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/capabilities/hardware-subsystems.json)"
if [ -e /etc/nuxel/capabilities/hardware-subsystems.json ] && [ ! -e /etc/nuxel/capabilities/hardware-subsystems.json.nuxel-rollback ]; then cp -a /etc/nuxel/capabilities/hardware-subsystems.json /etc/nuxel/capabilities/hardware-subsystems.json.nuxel-rollback; fi
test -f /etc/nuxel/capabilities/hardware-subsystems.json.nuxel-staged
printf '%s  %s\n' 806d076770519c57bead9090e00f5e6c6d05787956494f4d31c115fb91c920f8 /etc/nuxel/capabilities/hardware-subsystems.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/capabilities/hardware-subsystems.json.nuxel-staged /etc/nuxel/capabilities/hardware-subsystems.json
sha256sum /etc/nuxel/capabilities/hardware-subsystems.json | grep -q 806d076770519c57bead9090e00f5e6c6d05787956494f4d31c115fb91c920f8
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
