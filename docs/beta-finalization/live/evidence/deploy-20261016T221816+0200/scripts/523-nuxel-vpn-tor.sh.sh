#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-vpn-tor.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-vpn-tor.sh
# previous-hash: 477db0683555889934ef3e87b0b78939dc97c5bdd9b159d7c4d72d7bee854cba
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-vpn-tor.sh)"
if [ -e /usr/local/bin/nuxel-vpn-tor.sh ]; then cp -a /usr/local/bin/nuxel-vpn-tor.sh /usr/local/bin/nuxel-vpn-tor.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-vpn-tor.sh.nuxel-staged
printf '%s  %s\n' 477db0683555889934ef3e87b0b78939dc97c5bdd9b159d7c4d72d7bee854cba /usr/local/bin/nuxel-vpn-tor.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-vpn-tor.sh.nuxel-staged /usr/local/bin/nuxel-vpn-tor.sh
sha256sum /usr/local/bin/nuxel-vpn-tor.sh | grep -q 477db0683555889934ef3e87b0b78939dc97c5bdd9b159d7c4d72d7bee854cba
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-vpn-tor.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-vpn-tor.sh.nuxel-rollback /usr/local/bin/nuxel-vpn-tor.sh; true; fi
