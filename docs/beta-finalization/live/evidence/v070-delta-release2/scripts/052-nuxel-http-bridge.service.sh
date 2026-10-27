#!/bin/sh
# systemd version pins and canonical bridge-version documents -> /etc/systemd/system/nuxel-http-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-http-bridge.service
# previous-hash: 2cd5c0fb386d3bd02b9f74c77de3da54546d4a6c69d15a4f36a44a1582550007
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback.pre-v070-delta-release2 /etc/systemd/system/nuxel-http-bridge.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-http-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-http-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-http-bridge.service)"
if [ -e /etc/systemd/system/nuxel-http-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-http-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback.pre-v070-delta-release2; fi
test -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged
printf '%s  %s\n' 2cd5c0fb386d3bd02b9f74c77de3da54546d4a6c69d15a4f36a44a1582550007 /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged /etc/systemd/system/nuxel-http-bridge.service
sha256sum /etc/systemd/system/nuxel-http-bridge.service | grep -q 2cd5c0fb386d3bd02b9f74c77de3da54546d4a6c69d15a4f36a44a1582550007
echo INSTALL-OK
