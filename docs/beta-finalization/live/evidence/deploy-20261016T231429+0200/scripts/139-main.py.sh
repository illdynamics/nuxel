#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-firstboot/main.py
# previous-hash: ae85417b386249ca49def4a63eaf298fee11d6e5e4070be1b4233b76b488e88b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-staged
printf '%s  %s\n' ae85417b386249ca49def4a63eaf298fee11d6e5e4070be1b4233b76b488e88b /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py
sha256sum /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py | grep -q ae85417b386249ca49def4a63eaf298fee11d6e5e4070be1b4233b76b488e88b
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
