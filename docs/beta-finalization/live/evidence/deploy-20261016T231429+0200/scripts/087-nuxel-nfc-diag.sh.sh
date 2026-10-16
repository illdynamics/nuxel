#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-nfc-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-nfc-diag.sh
# previous-hash: 93546a357e4fa6e564b9739e99976f9d1e913bdd270b339ee964a46a5fceb9f8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-nfc-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-nfc-diag.sh.nuxel-rollback /usr/local/bin/nuxel-nfc-diag.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-nfc-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-nfc-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-nfc-diag.sh)"
if [ -e /usr/local/bin/nuxel-nfc-diag.sh ] && [ ! -e /usr/local/bin/nuxel-nfc-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-nfc-diag.sh /usr/local/bin/nuxel-nfc-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-nfc-diag.sh.nuxel-staged
printf '%s  %s\n' 93546a357e4fa6e564b9739e99976f9d1e913bdd270b339ee964a46a5fceb9f8 /usr/local/bin/nuxel-nfc-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-nfc-diag.sh.nuxel-staged /usr/local/bin/nuxel-nfc-diag.sh
sha256sum /usr/local/bin/nuxel-nfc-diag.sh | grep -q 93546a357e4fa6e564b9739e99976f9d1e913bdd270b339ee964a46a5fceb9f8
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
