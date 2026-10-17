#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/systemd/system/nuxel-camera-portal.service (service: None, risk: medium)
# staged source: shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service
# previous-hash: 12496cf23bfa66f1dcca0fc85f5f7a001413624f2c755b874dce6335948e8e0a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-camera-portal.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-camera-portal.service.nuxel-rollback /etc/systemd/system/nuxel-camera-portal.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-camera-portal.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-camera-portal.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-camera-portal.service)"
if [ -e /etc/systemd/system/nuxel-camera-portal.service ] && [ ! -e /etc/systemd/system/nuxel-camera-portal.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-camera-portal.service /etc/systemd/system/nuxel-camera-portal.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-camera-portal.service.nuxel-staged
printf '%s  %s\n' 12496cf23bfa66f1dcca0fc85f5f7a001413624f2c755b874dce6335948e8e0a /etc/systemd/system/nuxel-camera-portal.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-camera-portal.service.nuxel-staged /etc/systemd/system/nuxel-camera-portal.service
sha256sum /etc/systemd/system/nuxel-camera-portal.service | grep -q 12496cf23bfa66f1dcca0fc85f5f7a001413624f2c755b874dce6335948e8e0a
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
