#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/05-09_clipboard.png
# previous-hash: d159c288d7e297d26b07b36058e7b649d683fa8a4a2d9098430a9d0b9590b39d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png.nuxel-staged
printf '%s  %s\n' d159c288d7e297d26b07b36058e7b649d683fa8a4a2d9098430a9d0b9590b39d /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-09_clipboard.png | grep -q d159c288d7e297d26b07b36058e7b649d683fa8a4a2d9098430a9d0b9590b39d
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
