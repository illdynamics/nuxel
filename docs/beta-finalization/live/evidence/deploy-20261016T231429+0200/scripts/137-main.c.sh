#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-contacts/main.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-contacts/main.c
# previous-hash: 0af4c6e4c5b8c63565ea7465d72580ec4d4bdfb6bf1932e3464cb4de92724ca3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-contacts/main.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-contacts/main.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-contacts/main.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-contacts/main.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-contacts/main.c ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-contacts/main.c /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-staged
printf '%s  %s\n' 0af4c6e4c5b8c63565ea7465d72580ec4d4bdfb6bf1932e3464cb4de92724ca3 /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-contacts/main.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-contacts/main.c | grep -q 0af4c6e4c5b8c63565ea7465d72580ec4d4bdfb6bf1932e3464cb4de92724ca3
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
