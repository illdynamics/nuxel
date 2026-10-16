#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/leds/README.md (service: None, risk: medium)
# staged source: configs/nuxel/leds/README.md
# previous-hash: 6dce3fa5bc6ae6ef1975c3f770072292e00487b9cb57e8da6275981019943ac6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/leds/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/leds/README.md.nuxel-rollback /etc/nuxel/leds/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/leds/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/leds/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/leds/README.md)"
if [ -e /etc/nuxel/leds/README.md ] && [ ! -e /etc/nuxel/leds/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/leds/README.md /etc/nuxel/leds/README.md.nuxel-rollback; fi
test -f /etc/nuxel/leds/README.md.nuxel-staged
printf '%s  %s\n' 6dce3fa5bc6ae6ef1975c3f770072292e00487b9cb57e8da6275981019943ac6 /etc/nuxel/leds/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/leds/README.md.nuxel-staged /etc/nuxel/leds/README.md
sha256sum /etc/nuxel/leds/README.md | grep -q 6dce3fa5bc6ae6ef1975c3f770072292e00487b9cb57e8da6275981019943ac6
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
