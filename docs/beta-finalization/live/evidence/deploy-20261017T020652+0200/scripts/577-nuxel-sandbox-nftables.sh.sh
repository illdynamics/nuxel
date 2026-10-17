#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/local/bin/nuxel-sandbox-nftables.sh (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/nftables.sh
# previous-hash: 7ce53cd4db6494033672d9f448776e4e6b2b0471bb238aaf3002f73611733918
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-rollback /usr/local/bin/nuxel-sandbox-nftables.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-sandbox-nftables.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-sandbox-nftables.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-sandbox-nftables.sh)"
if [ -e /usr/local/bin/nuxel-sandbox-nftables.sh ] && [ ! -e /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-sandbox-nftables.sh /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-staged
printf '%s  %s\n' 7ce53cd4db6494033672d9f448776e4e6b2b0471bb238aaf3002f73611733918 /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-staged /usr/local/bin/nuxel-sandbox-nftables.sh
sha256sum /usr/local/bin/nuxel-sandbox-nftables.sh | grep -q 7ce53cd4db6494033672d9f448776e4e6b2b0471bb238aaf3002f73611733918
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
