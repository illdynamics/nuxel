#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/system/nuxel-rtc-check.timer (service: None, risk: medium)
# staged source: configs/nuxel/time/nuxel-rtc-check.timer
# previous-hash: afe177f852171e8ad470a2b3c8061164fe14b492bb8866390bbf9fc2060954ef
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-rtc-check.timer.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-rtc-check.timer.nuxel-rollback /etc/systemd/system/nuxel-rtc-check.timer; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-rtc-check.timer ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-rtc-check.timer | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-rtc-check.timer)"
if [ -e /etc/systemd/system/nuxel-rtc-check.timer ] && [ ! -e /etc/systemd/system/nuxel-rtc-check.timer.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-rtc-check.timer /etc/systemd/system/nuxel-rtc-check.timer.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-rtc-check.timer.nuxel-staged
printf '%s  %s\n' afe177f852171e8ad470a2b3c8061164fe14b492bb8866390bbf9fc2060954ef /etc/systemd/system/nuxel-rtc-check.timer.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-rtc-check.timer.nuxel-staged /etc/systemd/system/nuxel-rtc-check.timer
sha256sum /etc/systemd/system/nuxel-rtc-check.timer | grep -q afe177f852171e8ad470a2b3c8061164fe14b492bb8866390bbf9fc2060954ef
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
