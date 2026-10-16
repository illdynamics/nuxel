#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-microsd-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-microsd-diag.sh
# previous-hash: 001a0b77b773cca89f59ebe6d821092d9ccb14421801a5fae005b7a39f2c1042
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-microsd-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-microsd-diag.sh.nuxel-rollback /usr/local/bin/nuxel-microsd-diag.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-microsd-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-microsd-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-microsd-diag.sh)"
if [ -e /usr/local/bin/nuxel-microsd-diag.sh ] && [ ! -e /usr/local/bin/nuxel-microsd-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-microsd-diag.sh /usr/local/bin/nuxel-microsd-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-microsd-diag.sh.nuxel-staged
printf '%s  %s\n' 001a0b77b773cca89f59ebe6d821092d9ccb14421801a5fae005b7a39f2c1042 /usr/local/bin/nuxel-microsd-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-microsd-diag.sh.nuxel-staged /usr/local/bin/nuxel-microsd-diag.sh
sha256sum /usr/local/bin/nuxel-microsd-diag.sh | grep -q 001a0b77b773cca89f59ebe6d821092d9ccb14421801a5fae005b7a39f2c1042
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
