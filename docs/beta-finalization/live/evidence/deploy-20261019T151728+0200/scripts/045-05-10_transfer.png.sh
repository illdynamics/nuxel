#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/05-10_transfer.png
# previous-hash: e635ccaddfd565ca30bb8de87928472ebe4068f87ea09092aef455ff8d2d942d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png.nuxel-staged
printf '%s  %s\n' e635ccaddfd565ca30bb8de87928472ebe4068f87ea09092aef455ff8d2d942d /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-10_transfer.png | grep -q e635ccaddfd565ca30bb8de87928472ebe4068f87ea09092aef455ff8d2d942d
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
