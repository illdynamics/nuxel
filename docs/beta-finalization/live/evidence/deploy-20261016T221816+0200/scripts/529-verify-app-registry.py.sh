#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/verify-app-registry.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/verify-app-registry.py
# previous-hash: d4afac0c5d8e2b94d2691cf3d80191347800f78aba9ebb72654297b601948a66
set -eu
mkdir -p "$(dirname /usr/local/bin/verify-app-registry.py)"
if [ -e /usr/local/bin/verify-app-registry.py ]; then cp -a /usr/local/bin/verify-app-registry.py /usr/local/bin/verify-app-registry.py.nuxel-rollback; fi
test -f /usr/local/bin/verify-app-registry.py.nuxel-staged
printf '%s  %s\n' d4afac0c5d8e2b94d2691cf3d80191347800f78aba9ebb72654297b601948a66 /usr/local/bin/verify-app-registry.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/verify-app-registry.py.nuxel-staged /usr/local/bin/verify-app-registry.py
sha256sum /usr/local/bin/verify-app-registry.py | grep -q d4afac0c5d8e2b94d2691cf3d80191347800f78aba9ebb72654297b601948a66
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/verify-app-registry.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-app-registry.py.nuxel-rollback /usr/local/bin/verify-app-registry.py; true; fi
