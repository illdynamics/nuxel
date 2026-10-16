#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-audio-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-audio-diag.sh
# previous-hash: 0d5475367c8b5d9030176d3756f01ffecfddb56417fb8dbcc7a482bca298e21f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-audio-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-audio-diag.sh.nuxel-rollback /usr/local/bin/nuxel-audio-diag.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-audio-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-audio-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-audio-diag.sh)"
if [ -e /usr/local/bin/nuxel-audio-diag.sh ] && [ ! -e /usr/local/bin/nuxel-audio-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-audio-diag.sh /usr/local/bin/nuxel-audio-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-audio-diag.sh.nuxel-staged
printf '%s  %s\n' 0d5475367c8b5d9030176d3756f01ffecfddb56417fb8dbcc7a482bca298e21f /usr/local/bin/nuxel-audio-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-audio-diag.sh.nuxel-staged /usr/local/bin/nuxel-audio-diag.sh
sha256sum /usr/local/bin/nuxel-audio-diag.sh | grep -q 0d5475367c8b5d9030176d3756f01ffecfddb56417fb8dbcc7a482bca298e21f
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
