#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh (service: None, risk: medium)
# staged source: shell/nuxel-home-native/install-dev.sh
# previous-hash: 0d74587999fb69864d9bd1165314f2764dc4daef56640ebd76ea67b1b032010f
set -eu
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-staged
printf '%s  %s\n' 0d74587999fb69864d9bd1165314f2764dc4daef56640ebd76ea67b1b032010f /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh
sha256sum /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh | grep -q 0d74587999fb69864d9bd1165314f2764dc4daef56640ebd76ea67b1b032010f
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/install-dev.sh; true; fi
