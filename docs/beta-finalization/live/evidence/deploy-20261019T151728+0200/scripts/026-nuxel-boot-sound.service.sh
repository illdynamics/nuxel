#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /etc/systemd/system/nuxel-boot-sound.service (service: None, risk: high)
# staged source: services/nuxel-session/systemd/nuxel-boot-sound.service
# previous-hash: ed7648ebacd4b8116c7ad6b5939a5384ece081699450047e1d3b029f18abc206
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-boot-sound.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-boot-sound.service.nuxel-rollback /etc/systemd/system/nuxel-boot-sound.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-boot-sound.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-boot-sound.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-boot-sound.service)"
if [ -e /etc/systemd/system/nuxel-boot-sound.service ] && [ ! -e /etc/systemd/system/nuxel-boot-sound.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-boot-sound.service /etc/systemd/system/nuxel-boot-sound.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-boot-sound.service.nuxel-staged
printf '%s  %s\n' ed7648ebacd4b8116c7ad6b5939a5384ece081699450047e1d3b029f18abc206 /etc/systemd/system/nuxel-boot-sound.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-boot-sound.service.nuxel-staged /etc/systemd/system/nuxel-boot-sound.service
sha256sum /etc/systemd/system/nuxel-boot-sound.service | grep -q ed7648ebacd4b8116c7ad6b5939a5384ece081699450047e1d3b029f18abc206
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
