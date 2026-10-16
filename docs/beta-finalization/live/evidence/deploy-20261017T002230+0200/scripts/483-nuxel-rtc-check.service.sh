#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/system/nuxel-rtc-check.service (service: None, risk: medium)
# staged source: configs/nuxel/time/nuxel-rtc-check.service
# previous-hash: 48e1b033f2a61d0b397f26da5f6ca7498ed908631a8d98d795a96c78e4cc46d9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-rtc-check.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-rtc-check.service.nuxel-rollback /etc/systemd/system/nuxel-rtc-check.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-rtc-check.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-rtc-check.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-rtc-check.service)"
if [ -e /etc/systemd/system/nuxel-rtc-check.service ] && [ ! -e /etc/systemd/system/nuxel-rtc-check.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-rtc-check.service /etc/systemd/system/nuxel-rtc-check.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-rtc-check.service.nuxel-staged
printf '%s  %s\n' 48e1b033f2a61d0b397f26da5f6ca7498ed908631a8d98d795a96c78e4cc46d9 /etc/systemd/system/nuxel-rtc-check.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-rtc-check.service.nuxel-staged /etc/systemd/system/nuxel-rtc-check.service
sha256sum /etc/systemd/system/nuxel-rtc-check.service | grep -q 48e1b033f2a61d0b397f26da5f6ca7498ed908631a8d98d795a96c78e4cc46d9
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
