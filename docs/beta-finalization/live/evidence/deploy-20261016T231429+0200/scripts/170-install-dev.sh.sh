#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh (service: None, risk: medium)
# staged source: shell/nuxel-home-native/install-dev.sh
# previous-hash: 0d74587999fb69864d9bd1165314f2764dc4daef56640ebd76ea67b1b032010f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-staged
printf '%s  %s\n' 0d74587999fb69864d9bd1165314f2764dc4daef56640ebd76ea67b1b032010f /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh
sha256sum /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh | grep -q 0d74587999fb69864d9bd1165314f2764dc4daef56640ebd76ea67b1b032010f
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
