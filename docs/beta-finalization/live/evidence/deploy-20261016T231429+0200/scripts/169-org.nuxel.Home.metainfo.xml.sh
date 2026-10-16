#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml (service: None, risk: medium)
# staged source: shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml
# previous-hash: b6c5adf8e36bc19c6c5750a89d48bf30e0593e64d0db903bd7e23bcc4081a06d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml.nuxel-rollback /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml)"
if [ -e /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml ] && [ ! -e /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml.nuxel-rollback ]; then cp -a /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml.nuxel-rollback; fi
test -f /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml.nuxel-staged
printf '%s  %s\n' b6c5adf8e36bc19c6c5750a89d48bf30e0593e64d0db903bd7e23bcc4081a06d /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml.nuxel-staged /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml
sha256sum /usr/share/nuxel/shell/nuxel-home-native/data/org.nuxel.Home.metainfo.xml | grep -q b6c5adf8e36bc19c6c5750a89d48bf30e0593e64d0db903bd7e23bcc4081a06d
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
