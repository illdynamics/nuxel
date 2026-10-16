#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-messages/main.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-messages/main.c
# previous-hash: f75b6566a52444638c5c0182ea19fa06f7fd69597466b552837489dc909b794b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-messages/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-messages/main.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-messages/main.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-messages/main.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-messages/main.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-messages/main.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-messages/main.c ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-messages/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-messages/main.c /usr/lib/nuxel/src/shell/nuxel-messages/main.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-messages/main.c.nuxel-staged
printf '%s  %s\n' f75b6566a52444638c5c0182ea19fa06f7fd69597466b552837489dc909b794b /usr/lib/nuxel/src/shell/nuxel-messages/main.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-messages/main.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-messages/main.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-messages/main.c | grep -q f75b6566a52444638c5c0182ea19fa06f7fd69597466b552837489dc909b794b
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
