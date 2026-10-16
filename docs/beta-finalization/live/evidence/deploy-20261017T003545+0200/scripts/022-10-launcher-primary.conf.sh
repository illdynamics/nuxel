#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf (service: None, risk: medium)
# staged source: services/nuxel-session/systemd/nuxel-ui.service.d-10-launcher-primary.conf
# previous-hash: b26293afafb65bda1b23d28aaa08e9f066a918009e1c7b7f0e17e36dcef7f296
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf.nuxel-rollback /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf)"
if [ -e /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf ] && [ ! -e /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf.nuxel-staged
printf '%s  %s\n' b26293afafb65bda1b23d28aaa08e9f066a918009e1c7b7f0e17e36dcef7f296 /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf.nuxel-staged /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf
sha256sum /etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf | grep -q b26293afafb65bda1b23d28aaa08e9f066a918009e1c7b7f0e17e36dcef7f296
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
