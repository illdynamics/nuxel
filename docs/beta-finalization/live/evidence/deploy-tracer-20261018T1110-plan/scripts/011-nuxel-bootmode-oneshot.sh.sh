#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-bootmode-oneshot.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-bootmode-oneshot.sh
# previous-hash: 43c072be42ea63ae86b762a7797adc07560a4b2e9e5e4d55a6db338d0080b4ae
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-bootmode-oneshot.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-bootmode-oneshot.sh.nuxel-rollback /usr/local/bin/nuxel-bootmode-oneshot.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-bootmode-oneshot.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-bootmode-oneshot.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-bootmode-oneshot.sh)"
if [ -e /usr/local/bin/nuxel-bootmode-oneshot.sh ] && [ ! -e /usr/local/bin/nuxel-bootmode-oneshot.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-bootmode-oneshot.sh /usr/local/bin/nuxel-bootmode-oneshot.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-bootmode-oneshot.sh.nuxel-staged
printf '%s  %s\n' 43c072be42ea63ae86b762a7797adc07560a4b2e9e5e4d55a6db338d0080b4ae /usr/local/bin/nuxel-bootmode-oneshot.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-bootmode-oneshot.sh.nuxel-staged /usr/local/bin/nuxel-bootmode-oneshot.sh
sha256sum /usr/local/bin/nuxel-bootmode-oneshot.sh | grep -q 43c072be42ea63ae86b762a7797adc07560a4b2e9e5e4d55a6db338d0080b4ae
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
