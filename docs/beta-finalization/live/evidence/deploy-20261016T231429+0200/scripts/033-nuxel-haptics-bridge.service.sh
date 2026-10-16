#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/system/nuxel-haptics-bridge.service (service: None, risk: medium)
# staged source: configs/nuxel/haptics/nuxel-haptics-bridge.service
# previous-hash: 6b08d378c272d3d0b22d98b69d8422d064157b89e7faa03bbd5701bf0e631267
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-haptics-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-haptics-bridge.service.nuxel-rollback /etc/systemd/system/nuxel-haptics-bridge.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-haptics-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-haptics-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-haptics-bridge.service)"
if [ -e /etc/systemd/system/nuxel-haptics-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-haptics-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-haptics-bridge.service /etc/systemd/system/nuxel-haptics-bridge.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-haptics-bridge.service.nuxel-staged
printf '%s  %s\n' 6b08d378c272d3d0b22d98b69d8422d064157b89e7faa03bbd5701bf0e631267 /etc/systemd/system/nuxel-haptics-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-haptics-bridge.service.nuxel-staged /etc/systemd/system/nuxel-haptics-bridge.service
sha256sum /etc/systemd/system/nuxel-haptics-bridge.service | grep -q 6b08d378c272d3d0b22d98b69d8422d064157b89e7faa03bbd5701bf0e631267
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
