#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-haptics-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-haptics-diag.sh
# previous-hash: b48458ebcdcc06705b8bd11253fa2ef7e2ad2da4b1a53f8c1ea7a97e7615460b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-haptics-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-haptics-diag.sh.nuxel-rollback /usr/local/bin/nuxel-haptics-diag.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-haptics-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-haptics-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-haptics-diag.sh)"
if [ -e /usr/local/bin/nuxel-haptics-diag.sh ] && [ ! -e /usr/local/bin/nuxel-haptics-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-haptics-diag.sh /usr/local/bin/nuxel-haptics-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-haptics-diag.sh.nuxel-staged
printf '%s  %s\n' b48458ebcdcc06705b8bd11253fa2ef7e2ad2da4b1a53f8c1ea7a97e7615460b /usr/local/bin/nuxel-haptics-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-haptics-diag.sh.nuxel-staged /usr/local/bin/nuxel-haptics-diag.sh
sha256sum /usr/local/bin/nuxel-haptics-diag.sh | grep -q b48458ebcdcc06705b8bd11253fa2ef7e2ad2da4b1a53f8c1ea7a97e7615460b
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
