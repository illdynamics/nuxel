#!/bin/sh
# boot graph / session units -> /etc/systemd/system/nuxel-touch-arm.service (service: None, risk: high)
# staged source: services/nuxel-session/systemd/nuxel-touch-arm.service
# previous-hash: 85f7f880f9f875059c0d160331f96f93a22d2a2f055a2ca5b3f9c2bba816ab29
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-touch-arm.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-touch-arm.service.nuxel-rollback /etc/systemd/system/nuxel-touch-arm.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-touch-arm.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-touch-arm.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-touch-arm.service)"
if [ -e /etc/systemd/system/nuxel-touch-arm.service ] && [ ! -e /etc/systemd/system/nuxel-touch-arm.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-touch-arm.service /etc/systemd/system/nuxel-touch-arm.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-touch-arm.service.nuxel-staged
printf '%s  %s\n' 85f7f880f9f875059c0d160331f96f93a22d2a2f055a2ca5b3f9c2bba816ab29 /etc/systemd/system/nuxel-touch-arm.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-touch-arm.service.nuxel-staged /etc/systemd/system/nuxel-touch-arm.service
sha256sum /etc/systemd/system/nuxel-touch-arm.service | grep -q 85f7f880f9f875059c0d160331f96f93a22d2a2f055a2ca5b3f9c2bba816ab29
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
