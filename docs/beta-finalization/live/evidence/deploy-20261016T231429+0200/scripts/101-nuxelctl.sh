#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxelctl (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxelctl
# previous-hash: b002daf2e1c79ef6cd9a60f7f868470534bec592e01d1c945ab447bb4203bf1b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxelctl.nuxel-rollback ]; then cp -a /usr/local/bin/nuxelctl.nuxel-rollback /usr/local/bin/nuxelctl; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxelctl ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxelctl | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxelctl)"
if [ -e /usr/local/bin/nuxelctl ] && [ ! -e /usr/local/bin/nuxelctl.nuxel-rollback ]; then cp -a /usr/local/bin/nuxelctl /usr/local/bin/nuxelctl.nuxel-rollback; fi
test -f /usr/local/bin/nuxelctl.nuxel-staged
printf '%s  %s\n' b002daf2e1c79ef6cd9a60f7f868470534bec592e01d1c945ab447bb4203bf1b /usr/local/bin/nuxelctl.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxelctl.nuxel-staged /usr/local/bin/nuxelctl
sha256sum /usr/local/bin/nuxelctl | grep -q b002daf2e1c79ef6cd9a60f7f868470534bec592e01d1c945ab447bb4203bf1b
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
