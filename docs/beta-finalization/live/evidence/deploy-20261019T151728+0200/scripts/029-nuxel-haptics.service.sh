#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /etc/systemd/system/nuxel-haptics.service (service: None, risk: high)
# staged source: services/nuxel-haptics/nuxel-haptics.service
# previous-hash: 4dded21d2e83efd7e2448431d671f8a6102d7fa0210712d5b0a862be7db53846
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-haptics.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-haptics.service.nuxel-rollback /etc/systemd/system/nuxel-haptics.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-haptics.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-haptics.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-haptics.service)"
if [ -e /etc/systemd/system/nuxel-haptics.service ] && [ ! -e /etc/systemd/system/nuxel-haptics.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-haptics.service /etc/systemd/system/nuxel-haptics.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-haptics.service.nuxel-staged
printf '%s  %s\n' 4dded21d2e83efd7e2448431d671f8a6102d7fa0210712d5b0a862be7db53846 /etc/systemd/system/nuxel-haptics.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-haptics.service.nuxel-staged /etc/systemd/system/nuxel-haptics.service
sha256sum /etc/systemd/system/nuxel-haptics.service | grep -q 4dded21d2e83efd7e2448431d671f8a6102d7fa0210712d5b0a862be7db53846
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
