#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/verify-app-inventory.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/verify-app-inventory.py
# previous-hash: f18ccad895d647ed7b5d5f63d6b8f7ee1ee9ea3dc91cb0a369764cb85b9da059
set -eu
mkdir -p "$(dirname /usr/local/bin/verify-app-inventory.py)"
if [ -e /usr/local/bin/verify-app-inventory.py ]; then cp -a /usr/local/bin/verify-app-inventory.py /usr/local/bin/verify-app-inventory.py.nuxel-rollback; fi
test -f /usr/local/bin/verify-app-inventory.py.nuxel-staged
printf '%s  %s\n' f18ccad895d647ed7b5d5f63d6b8f7ee1ee9ea3dc91cb0a369764cb85b9da059 /usr/local/bin/verify-app-inventory.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/verify-app-inventory.py.nuxel-staged /usr/local/bin/verify-app-inventory.py
sha256sum /usr/local/bin/verify-app-inventory.py | grep -q f18ccad895d647ed7b5d5f63d6b8f7ee1ee9ea3dc91cb0a369764cb85b9da059
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/verify-app-inventory.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-app-inventory.py.nuxel-rollback /usr/local/bin/verify-app-inventory.py; true; fi
