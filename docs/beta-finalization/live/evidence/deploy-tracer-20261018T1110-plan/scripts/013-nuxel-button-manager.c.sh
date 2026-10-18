#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-button-manager.c (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-button-manager.c
# previous-hash: c331b4e4ce1b82e9d969be8bd4228d4dabb876a34754b8d54d4d2d8bf1c03154
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-button-manager.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-manager.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/nuxel-button-manager.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-button-manager.c)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-manager.c ] && [ ! -e /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-manager.c /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-staged
printf '%s  %s\n' c331b4e4ce1b82e9d969be8bd4228d4dabb876a34754b8d54d4d2d8bf1c03154 /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-button-manager.c
sha256sum /usr/lib/nuxel/src/a33/nuxel-button-manager.c | grep -q c331b4e4ce1b82e9d969be8bd4228d4dabb876a34754b8d54d4d2d8bf1c03154
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
