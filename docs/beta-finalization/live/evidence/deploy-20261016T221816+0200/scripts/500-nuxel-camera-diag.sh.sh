#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-camera-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-camera-diag.sh
# previous-hash: e742baad3fcdd8ab89be848d50a4cd2c788f3f20f069843d7fe415b60abcad6e
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-camera-diag.sh)"
if [ -e /usr/local/bin/nuxel-camera-diag.sh ]; then cp -a /usr/local/bin/nuxel-camera-diag.sh /usr/local/bin/nuxel-camera-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-camera-diag.sh.nuxel-staged
printf '%s  %s\n' e742baad3fcdd8ab89be848d50a4cd2c788f3f20f069843d7fe415b60abcad6e /usr/local/bin/nuxel-camera-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-camera-diag.sh.nuxel-staged /usr/local/bin/nuxel-camera-diag.sh
sha256sum /usr/local/bin/nuxel-camera-diag.sh | grep -q e742baad3fcdd8ab89be848d50a4cd2c788f3f20f069843d7fe415b60abcad6e
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-camera-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-camera-diag.sh.nuxel-rollback /usr/local/bin/nuxel-camera-diag.sh; true; fi
