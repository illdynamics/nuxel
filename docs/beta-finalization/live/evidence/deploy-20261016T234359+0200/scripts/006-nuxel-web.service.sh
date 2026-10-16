#!/bin/sh
# boot graph / session units -> /etc/systemd/system/nuxel-web.service (service: None, risk: high)
# staged source: services/nuxel-web.service
# previous-hash: e4c692b4e14134cef9b75f7b881bc8e068bce32438ffdc9bf9c4924ffcebc903
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-web.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-web.service.nuxel-rollback /etc/systemd/system/nuxel-web.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-web.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-web.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-web.service)"
if [ -e /etc/systemd/system/nuxel-web.service ] && [ ! -e /etc/systemd/system/nuxel-web.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-web.service /etc/systemd/system/nuxel-web.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-web.service.nuxel-staged
printf '%s  %s\n' e4c692b4e14134cef9b75f7b881bc8e068bce32438ffdc9bf9c4924ffcebc903 /etc/systemd/system/nuxel-web.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-web.service.nuxel-staged /etc/systemd/system/nuxel-web.service
sha256sum /etc/systemd/system/nuxel-web.service | grep -q e4c692b4e14134cef9b75f7b881bc8e068bce32438ffdc9bf9c4924ffcebc903
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
