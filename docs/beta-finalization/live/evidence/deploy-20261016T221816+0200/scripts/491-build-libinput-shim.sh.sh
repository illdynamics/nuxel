#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/build-libinput-shim.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/build-libinput-shim.sh
# previous-hash: 667f7fadb7ee475e130688d884e116fc2de12512b03941242fbcb1f6399e300c
set -eu
mkdir -p "$(dirname /usr/local/bin/build-libinput-shim.sh)"
if [ -e /usr/local/bin/build-libinput-shim.sh ]; then cp -a /usr/local/bin/build-libinput-shim.sh /usr/local/bin/build-libinput-shim.sh.nuxel-rollback; fi
test -f /usr/local/bin/build-libinput-shim.sh.nuxel-staged
printf '%s  %s\n' 667f7fadb7ee475e130688d884e116fc2de12512b03941242fbcb1f6399e300c /usr/local/bin/build-libinput-shim.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/build-libinput-shim.sh.nuxel-staged /usr/local/bin/build-libinput-shim.sh
sha256sum /usr/local/bin/build-libinput-shim.sh | grep -q 667f7fadb7ee475e130688d884e116fc2de12512b03941242fbcb1f6399e300c
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/build-libinput-shim.sh.nuxel-rollback ]; then cp -a /usr/local/bin/build-libinput-shim.sh.nuxel-rollback /usr/local/bin/build-libinput-shim.sh; true; fi
