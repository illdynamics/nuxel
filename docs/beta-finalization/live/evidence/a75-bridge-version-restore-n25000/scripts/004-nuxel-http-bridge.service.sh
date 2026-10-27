#!/bin/sh
# systemd unit env pins + bridge-version.json + shared PWA bridge honesty fallback -> /etc/systemd/system/nuxel-http-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-http-bridge.service
# previous-hash: 97944ab8d75261cf335468efae2bb76cac4da4a84c7607b615fddc59b59e5def
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback /etc/systemd/system/nuxel-http-bridge.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-http-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-http-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-http-bridge.service)"
if [ -e /etc/systemd/system/nuxel-http-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged
printf '%s  %s\n' 97944ab8d75261cf335468efae2bb76cac4da4a84c7607b615fddc59b59e5def /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged /etc/systemd/system/nuxel-http-bridge.service
sha256sum /etc/systemd/system/nuxel-http-bridge.service | grep -q 97944ab8d75261cf335468efae2bb76cac4da4a84c7607b615fddc59b59e5def
echo INSTALL-OK
