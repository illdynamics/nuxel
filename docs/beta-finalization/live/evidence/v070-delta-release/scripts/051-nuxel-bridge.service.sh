#!/bin/sh
# systemd version pins and canonical bridge-version documents -> /etc/systemd/system/nuxel-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-bridge.service
# previous-hash: 45b5178db8ced3269eafc22e548232cac12924b6fbb6e1448ac65c01d9c34c96
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-v070-delta-release ]; then cp -a /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-v070-delta-release /etc/systemd/system/nuxel-bridge.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-bridge.service)"
if [ -e /etc/systemd/system/nuxel-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-bridge.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-v070-delta-release ]; then cp -a /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-v070-delta-release; fi
test -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged
printf '%s  %s\n' 45b5178db8ced3269eafc22e548232cac12924b6fbb6e1448ac65c01d9c34c96 /etc/systemd/system/nuxel-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged /etc/systemd/system/nuxel-bridge.service
sha256sum /etc/systemd/system/nuxel-bridge.service | grep -q 45b5178db8ced3269eafc22e548232cac12924b6fbb6e1448ac65c01d9c34c96
echo INSTALL-OK
