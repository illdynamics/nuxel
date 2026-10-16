#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-phone-data/run-tests.sh
# previous-hash: ff3a8fa96f1007762efa2245910372d910dd56d3b930242e05eb6ca66290b42f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh.nuxel-staged
printf '%s  %s\n' ff3a8fa96f1007762efa2245910372d910dd56d3b930242e05eb6ca66290b42f /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh
sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/run-tests.sh | grep -q ff3a8fa96f1007762efa2245910372d910dd56d3b930242e05eb6ca66290b42f
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
