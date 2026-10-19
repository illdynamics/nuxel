#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/share/nuxel/probes/touch-probe.html (service: None, risk: medium)
# staged source: tools/s10plus/a33/touch-probe.html
# previous-hash: aea597a1b6cb77a5e7af497a63a4900b59000498a8ccedf6d5998ae8371aad21
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/probes/touch-probe.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/probes/touch-probe.html.nuxel-rollback /usr/share/nuxel/probes/touch-probe.html; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/probes/touch-probe.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/probes/touch-probe.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/probes/touch-probe.html)"
if [ -e /usr/share/nuxel/probes/touch-probe.html ] && [ ! -e /usr/share/nuxel/probes/touch-probe.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/probes/touch-probe.html /usr/share/nuxel/probes/touch-probe.html.nuxel-rollback; fi
test -f /usr/share/nuxel/probes/touch-probe.html.nuxel-staged
printf '%s  %s\n' aea597a1b6cb77a5e7af497a63a4900b59000498a8ccedf6d5998ae8371aad21 /usr/share/nuxel/probes/touch-probe.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/probes/touch-probe.html.nuxel-staged /usr/share/nuxel/probes/touch-probe.html
sha256sum /usr/share/nuxel/probes/touch-probe.html | grep -q aea597a1b6cb77a5e7af497a63a4900b59000498a8ccedf6d5998ae8371aad21
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
