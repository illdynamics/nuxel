#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/build-a33-buttons.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/build-a33-buttons.sh
# previous-hash: 412e7e1857366d87fa2a2c15c65392c2e9084acf4a76dec3868e500b5a398d48
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/build-a33-buttons.sh.nuxel-rollback ]; then cp -a /usr/local/bin/build-a33-buttons.sh.nuxel-rollback /usr/local/bin/build-a33-buttons.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/build-a33-buttons.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/build-a33-buttons.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/build-a33-buttons.sh)"
if [ -e /usr/local/bin/build-a33-buttons.sh ] && [ ! -e /usr/local/bin/build-a33-buttons.sh.nuxel-rollback ]; then cp -a /usr/local/bin/build-a33-buttons.sh /usr/local/bin/build-a33-buttons.sh.nuxel-rollback; fi
test -f /usr/local/bin/build-a33-buttons.sh.nuxel-staged
printf '%s  %s\n' 412e7e1857366d87fa2a2c15c65392c2e9084acf4a76dec3868e500b5a398d48 /usr/local/bin/build-a33-buttons.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/build-a33-buttons.sh.nuxel-staged /usr/local/bin/build-a33-buttons.sh
sha256sum /usr/local/bin/build-a33-buttons.sh | grep -q 412e7e1857366d87fa2a2c15c65392c2e9084acf4a76dec3868e500b5a398d48
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
