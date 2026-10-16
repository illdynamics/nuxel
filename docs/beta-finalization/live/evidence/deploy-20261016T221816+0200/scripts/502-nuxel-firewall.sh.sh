#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-firewall.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-firewall.sh
# previous-hash: e246c41ea703b5dd5a4e07a033896a378ea98a5ceeffd332867684073305dd1f
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-firewall.sh)"
if [ -e /usr/local/bin/nuxel-firewall.sh ]; then cp -a /usr/local/bin/nuxel-firewall.sh /usr/local/bin/nuxel-firewall.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-firewall.sh.nuxel-staged
printf '%s  %s\n' e246c41ea703b5dd5a4e07a033896a378ea98a5ceeffd332867684073305dd1f /usr/local/bin/nuxel-firewall.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-firewall.sh.nuxel-staged /usr/local/bin/nuxel-firewall.sh
sha256sum /usr/local/bin/nuxel-firewall.sh | grep -q e246c41ea703b5dd5a4e07a033896a378ea98a5ceeffd332867684073305dd1f
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-firewall.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-firewall.sh.nuxel-rollback /usr/local/bin/nuxel-firewall.sh; true; fi
