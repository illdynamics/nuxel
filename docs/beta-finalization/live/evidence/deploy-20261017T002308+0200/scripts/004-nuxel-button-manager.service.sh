#!/bin/sh
# boot graph / session units -> /etc/systemd/system/nuxel-button-manager.service (service: None, risk: high)
# staged source: services/nuxel-session/systemd/nuxel-button-manager.service
# previous-hash: c0bc10c448a500efc5fc4edff6d308ae69d583bffc6da6c90604371547b3c1a9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-button-manager.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-button-manager.service.nuxel-rollback /etc/systemd/system/nuxel-button-manager.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-button-manager.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-button-manager.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-button-manager.service)"
if [ -e /etc/systemd/system/nuxel-button-manager.service ] && [ ! -e /etc/systemd/system/nuxel-button-manager.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-button-manager.service /etc/systemd/system/nuxel-button-manager.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-button-manager.service.nuxel-staged
printf '%s  %s\n' c0bc10c448a500efc5fc4edff6d308ae69d583bffc6da6c90604371547b3c1a9 /etc/systemd/system/nuxel-button-manager.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-button-manager.service.nuxel-staged /etc/systemd/system/nuxel-button-manager.service
sha256sum /etc/systemd/system/nuxel-button-manager.service | grep -q c0bc10c448a500efc5fc4edff6d308ae69d583bffc6da6c90604371547b3c1a9
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
