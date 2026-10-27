#!/bin/sh
# systemd unit env pins + bridge-version.json + shared PWA bridge honesty fallback -> /etc/systemd/system/nuxel-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-bridge.service
# previous-hash: 67ce1cea694617887d65142f35e110a705aabc31eef76430915b14f1327399a0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-a75-noop-n25000-1 ]; then cp -a /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-a75-noop-n25000-1 /etc/systemd/system/nuxel-bridge.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-bridge.service)"
if [ -e /etc/systemd/system/nuxel-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-bridge.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-a75-noop-n25000-1 ]; then cp -a /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-a75-noop-n25000-1; fi
test -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged
printf '%s  %s\n' 67ce1cea694617887d65142f35e110a705aabc31eef76430915b14f1327399a0 /etc/systemd/system/nuxel-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged /etc/systemd/system/nuxel-bridge.service
sha256sum /etc/systemd/system/nuxel-bridge.service | grep -q 67ce1cea694617887d65142f35e110a705aabc31eef76430915b14f1327399a0
echo INSTALL-OK
