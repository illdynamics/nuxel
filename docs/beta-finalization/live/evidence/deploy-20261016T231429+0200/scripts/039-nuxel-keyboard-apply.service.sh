#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/system/nuxel-keyboard-apply.service (service: None, risk: medium)
# staged source: configs/nuxel/keyboard/nuxel-keyboard-apply.service
# previous-hash: c9795ca275315ee2ddd4be6b070f5a70d5a028afc41be75c9f5ce270e9b56475
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-keyboard-apply.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-keyboard-apply.service.nuxel-rollback /etc/systemd/system/nuxel-keyboard-apply.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-keyboard-apply.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-keyboard-apply.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-keyboard-apply.service)"
if [ -e /etc/systemd/system/nuxel-keyboard-apply.service ] && [ ! -e /etc/systemd/system/nuxel-keyboard-apply.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-keyboard-apply.service /etc/systemd/system/nuxel-keyboard-apply.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-keyboard-apply.service.nuxel-staged
printf '%s  %s\n' c9795ca275315ee2ddd4be6b070f5a70d5a028afc41be75c9f5ce270e9b56475 /etc/systemd/system/nuxel-keyboard-apply.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-keyboard-apply.service.nuxel-staged /etc/systemd/system/nuxel-keyboard-apply.service
sha256sum /etc/systemd/system/nuxel-keyboard-apply.service | grep -q c9795ca275315ee2ddd4be6b070f5a70d5a028afc41be75c9f5ce270e9b56475
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
