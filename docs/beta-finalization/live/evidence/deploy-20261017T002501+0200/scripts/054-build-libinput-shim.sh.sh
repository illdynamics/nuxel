#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/build-libinput-shim.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/build-libinput-shim.sh
# previous-hash: 667f7fadb7ee475e130688d884e116fc2de12512b03941242fbcb1f6399e300c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/build-libinput-shim.sh.nuxel-rollback ]; then cp -a /usr/local/bin/build-libinput-shim.sh.nuxel-rollback /usr/local/bin/build-libinput-shim.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/build-libinput-shim.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/build-libinput-shim.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/build-libinput-shim.sh)"
if [ -e /usr/local/bin/build-libinput-shim.sh ] && [ ! -e /usr/local/bin/build-libinput-shim.sh.nuxel-rollback ]; then cp -a /usr/local/bin/build-libinput-shim.sh /usr/local/bin/build-libinput-shim.sh.nuxel-rollback; fi
test -f /usr/local/bin/build-libinput-shim.sh.nuxel-staged
printf '%s  %s\n' 667f7fadb7ee475e130688d884e116fc2de12512b03941242fbcb1f6399e300c /usr/local/bin/build-libinput-shim.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/build-libinput-shim.sh.nuxel-staged /usr/local/bin/build-libinput-shim.sh
sha256sum /usr/local/bin/build-libinput-shim.sh | grep -q 667f7fadb7ee475e130688d884e116fc2de12512b03941242fbcb1f6399e300c
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
