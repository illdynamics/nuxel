#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-libinput-path.c (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-libinput-path.c
# previous-hash: f94240412b731233ad0e93de24d20283f55fc0d0b1f74aa1cddc9f19265e598f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/nuxel-libinput-path.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-libinput-path.c.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-libinput-path.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/nuxel-libinput-path.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/nuxel-libinput-path.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-libinput-path.c)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-libinput-path.c ] && [ ! -e /usr/lib/nuxel/src/a33/nuxel-libinput-path.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-libinput-path.c /usr/lib/nuxel/src/a33/nuxel-libinput-path.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-libinput-path.c.nuxel-staged
printf '%s  %s\n' f94240412b731233ad0e93de24d20283f55fc0d0b1f74aa1cddc9f19265e598f /usr/lib/nuxel/src/a33/nuxel-libinput-path.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-libinput-path.c.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-libinput-path.c
sha256sum /usr/lib/nuxel/src/a33/nuxel-libinput-path.c | grep -q f94240412b731233ad0e93de24d20283f55fc0d0b1f74aa1cddc9f19265e598f
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
