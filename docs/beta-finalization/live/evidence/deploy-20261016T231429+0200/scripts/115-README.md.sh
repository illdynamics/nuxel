#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-console/README.md (service: None, risk: medium)
# staged source: services/nuxel-console/README.md
# previous-hash: b6b0fec2c3759ae3f5a80aafb41f61c5efb3351b856cdf3114e9a6450ed1b657
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-console/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-console/README.md.nuxel-rollback /usr/lib/nuxel/nuxel-console/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-console/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-console/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-console/README.md)"
if [ -e /usr/lib/nuxel/nuxel-console/README.md ] && [ ! -e /usr/lib/nuxel/nuxel-console/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-console/README.md /usr/lib/nuxel/nuxel-console/README.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-console/README.md.nuxel-staged
printf '%s  %s\n' b6b0fec2c3759ae3f5a80aafb41f61c5efb3351b856cdf3114e9a6450ed1b657 /usr/lib/nuxel/nuxel-console/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-console/README.md.nuxel-staged /usr/lib/nuxel/nuxel-console/README.md
sha256sum /usr/lib/nuxel/nuxel-console/README.md | grep -q b6b0fec2c3759ae3f5a80aafb41f61c5efb3351b856cdf3114e9a6450ed1b657
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
systemctl daemon-reload
echo INSTALL-OK
