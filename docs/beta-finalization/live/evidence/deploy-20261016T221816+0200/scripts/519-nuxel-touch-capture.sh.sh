#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-touch-capture.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-touch-capture.sh
# previous-hash: 93b7179e2ce7a2171b77fc1284fb7f0dc5bdbb36d8453ac5d945519136de57b4
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-touch-capture.sh)"
if [ -e /usr/local/bin/nuxel-touch-capture.sh ]; then cp -a /usr/local/bin/nuxel-touch-capture.sh /usr/local/bin/nuxel-touch-capture.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-touch-capture.sh.nuxel-staged
printf '%s  %s\n' 93b7179e2ce7a2171b77fc1284fb7f0dc5bdbb36d8453ac5d945519136de57b4 /usr/local/bin/nuxel-touch-capture.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-touch-capture.sh.nuxel-staged /usr/local/bin/nuxel-touch-capture.sh
sha256sum /usr/local/bin/nuxel-touch-capture.sh | grep -q 93b7179e2ce7a2171b77fc1284fb7f0dc5bdbb36d8453ac5d945519136de57b4
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-touch-capture.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-touch-capture.sh.nuxel-rollback /usr/local/bin/nuxel-touch-capture.sh; true; fi
