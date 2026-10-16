#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/sensors/README.md (service: None, risk: medium)
# staged source: configs/nuxel/sensors/README.md
# previous-hash: 40aca4b6bd6c078a77927ffe7a8bdb3ade19266033ce3972435e68f4666ddebb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sensors/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/sensors/README.md.nuxel-rollback /etc/nuxel/sensors/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sensors/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sensors/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sensors/README.md)"
if [ -e /etc/nuxel/sensors/README.md ] && [ ! -e /etc/nuxel/sensors/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/sensors/README.md /etc/nuxel/sensors/README.md.nuxel-rollback; fi
test -f /etc/nuxel/sensors/README.md.nuxel-staged
printf '%s  %s\n' 40aca4b6bd6c078a77927ffe7a8bdb3ade19266033ce3972435e68f4666ddebb /etc/nuxel/sensors/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sensors/README.md.nuxel-staged /etc/nuxel/sensors/README.md
sha256sum /etc/nuxel/sensors/README.md | grep -q 40aca4b6bd6c078a77927ffe7a8bdb3ade19266033ce3972435e68f4666ddebb
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
