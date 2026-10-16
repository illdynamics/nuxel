#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-firewall.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-firewall.sh
# previous-hash: e246c41ea703b5dd5a4e07a033896a378ea98a5ceeffd332867684073305dd1f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-firewall.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-firewall.sh.nuxel-rollback /usr/local/bin/nuxel-firewall.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-firewall.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-firewall.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-firewall.sh)"
if [ -e /usr/local/bin/nuxel-firewall.sh ] && [ ! -e /usr/local/bin/nuxel-firewall.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-firewall.sh /usr/local/bin/nuxel-firewall.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-firewall.sh.nuxel-staged
printf '%s  %s\n' e246c41ea703b5dd5a4e07a033896a378ea98a5ceeffd332867684073305dd1f /usr/local/bin/nuxel-firewall.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-firewall.sh.nuxel-staged /usr/local/bin/nuxel-firewall.sh
sha256sum /usr/local/bin/nuxel-firewall.sh | grep -q e246c41ea703b5dd5a4e07a033896a378ea98a5ceeffd332867684073305dd1f
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
