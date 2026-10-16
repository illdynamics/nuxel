#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-led-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-led-diag.sh
# previous-hash: d24124105fdcedb056dcec0c3aee9b010d26b42ae01397bfe733393670532b83
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-led-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-led-diag.sh.nuxel-rollback /usr/local/bin/nuxel-led-diag.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-led-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-led-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-led-diag.sh)"
if [ -e /usr/local/bin/nuxel-led-diag.sh ] && [ ! -e /usr/local/bin/nuxel-led-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-led-diag.sh /usr/local/bin/nuxel-led-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-led-diag.sh.nuxel-staged
printf '%s  %s\n' d24124105fdcedb056dcec0c3aee9b010d26b42ae01397bfe733393670532b83 /usr/local/bin/nuxel-led-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-led-diag.sh.nuxel-staged /usr/local/bin/nuxel-led-diag.sh
sha256sum /usr/local/bin/nuxel-led-diag.sh | grep -q d24124105fdcedb056dcec0c3aee9b010d26b42ae01397bfe733393670532b83
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
