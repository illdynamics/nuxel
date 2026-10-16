#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/local/bin/nuxel-uninstall-helper.sh (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-uninstall-helper.sh
# previous-hash: 3c7617a55bc34626d55a24f5ce0c527cf3ba15bdb2713357a714da35779d36d2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-uninstall-helper.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-uninstall-helper.sh.nuxel-rollback /usr/local/bin/nuxel-uninstall-helper.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-uninstall-helper.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-uninstall-helper.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-uninstall-helper.sh)"
if [ -e /usr/local/bin/nuxel-uninstall-helper.sh ] && [ ! -e /usr/local/bin/nuxel-uninstall-helper.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-uninstall-helper.sh /usr/local/bin/nuxel-uninstall-helper.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-uninstall-helper.sh.nuxel-staged
printf '%s  %s\n' 3c7617a55bc34626d55a24f5ce0c527cf3ba15bdb2713357a714da35779d36d2 /usr/local/bin/nuxel-uninstall-helper.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-uninstall-helper.sh.nuxel-staged /usr/local/bin/nuxel-uninstall-helper.sh
sha256sum /usr/local/bin/nuxel-uninstall-helper.sh | grep -q 3c7617a55bc34626d55a24f5ce0c527cf3ba15bdb2713357a714da35779d36d2
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
