#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-keyboard-apply.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-keyboard-apply.sh
# previous-hash: 2794f65d2b9c8a6efda18b68e3b13f6f19338be0dd55c5fabde767ad87f40d50
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-rollback /usr/local/bin/nuxel-keyboard-apply.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-keyboard-apply.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-keyboard-apply.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-keyboard-apply.sh)"
if [ -e /usr/local/bin/nuxel-keyboard-apply.sh ] && [ ! -e /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-keyboard-apply.sh /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-staged
printf '%s  %s\n' 2794f65d2b9c8a6efda18b68e3b13f6f19338be0dd55c5fabde767ad87f40d50 /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-staged /usr/local/bin/nuxel-keyboard-apply.sh
sha256sum /usr/local/bin/nuxel-keyboard-apply.sh | grep -q 2794f65d2b9c8a6efda18b68e3b13f6f19338be0dd55c5fabde767ad87f40d50
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
