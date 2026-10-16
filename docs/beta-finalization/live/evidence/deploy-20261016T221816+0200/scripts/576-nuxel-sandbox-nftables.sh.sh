#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/local/bin/nuxel-sandbox-nftables.sh (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/nftables.sh
# previous-hash: 7ce53cd4db6494033672d9f448776e4e6b2b0471bb238aaf3002f73611733918
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-sandbox-nftables.sh)"
if [ -e /usr/local/bin/nuxel-sandbox-nftables.sh ]; then cp -a /usr/local/bin/nuxel-sandbox-nftables.sh /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-staged
printf '%s  %s\n' 7ce53cd4db6494033672d9f448776e4e6b2b0471bb238aaf3002f73611733918 /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-staged /usr/local/bin/nuxel-sandbox-nftables.sh
sha256sum /usr/local/bin/nuxel-sandbox-nftables.sh | grep -q 7ce53cd4db6494033672d9f448776e4e6b2b0471bb238aaf3002f73611733918
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-sandbox-nftables.sh.nuxel-rollback /usr/local/bin/nuxel-sandbox-nftables.sh; true; fi
