#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-vpn-tor.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-vpn-tor.sh
# previous-hash: 42f206307dafbe8201de99127e82fb0fe372617b88f99480a90f5e5864b06acf
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-vpn-tor.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-vpn-tor.sh.nuxel-rollback /usr/local/bin/nuxel-vpn-tor.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-vpn-tor.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-vpn-tor.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-vpn-tor.sh)"
if [ -e /usr/local/bin/nuxel-vpn-tor.sh ] && [ ! -e /usr/local/bin/nuxel-vpn-tor.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-vpn-tor.sh /usr/local/bin/nuxel-vpn-tor.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-vpn-tor.sh.nuxel-staged
printf '%s  %s\n' 42f206307dafbe8201de99127e82fb0fe372617b88f99480a90f5e5864b06acf /usr/local/bin/nuxel-vpn-tor.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-vpn-tor.sh.nuxel-staged /usr/local/bin/nuxel-vpn-tor.sh
sha256sum /usr/local/bin/nuxel-vpn-tor.sh | grep -q 42f206307dafbe8201de99127e82fb0fe372617b88f99480a90f5e5864b06acf
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
