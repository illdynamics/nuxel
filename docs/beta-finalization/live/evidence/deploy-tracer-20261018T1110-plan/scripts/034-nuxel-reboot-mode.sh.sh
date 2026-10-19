#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-reboot-mode.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-reboot-mode.sh
# previous-hash: a2822cffe942064cc31ad6a90a05747609339cac21cf0e9c127745f65f1cd0bc
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-reboot-mode.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-reboot-mode.sh.nuxel-rollback /usr/local/bin/nuxel-reboot-mode.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-reboot-mode.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-reboot-mode.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-reboot-mode.sh)"
if [ -e /usr/local/bin/nuxel-reboot-mode.sh ] && [ ! -e /usr/local/bin/nuxel-reboot-mode.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-reboot-mode.sh /usr/local/bin/nuxel-reboot-mode.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-reboot-mode.sh.nuxel-staged
printf '%s  %s\n' a2822cffe942064cc31ad6a90a05747609339cac21cf0e9c127745f65f1cd0bc /usr/local/bin/nuxel-reboot-mode.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-reboot-mode.sh.nuxel-staged /usr/local/bin/nuxel-reboot-mode.sh
sha256sum /usr/local/bin/nuxel-reboot-mode.sh | grep -q a2822cffe942064cc31ad6a90a05747609339cac21cf0e9c127745f65f1cd0bc
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
