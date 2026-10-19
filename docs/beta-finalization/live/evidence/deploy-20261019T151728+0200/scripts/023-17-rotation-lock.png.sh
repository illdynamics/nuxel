#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png
# previous-hash: 99ede17594b30f04ed2904f7460335857e44f2d11a7335d4f4815ce76a0fef65
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png.nuxel-staged
printf '%s  %s\n' 99ede17594b30f04ed2904f7460335857e44f2d11a7335d4f4815ce76a0fef65 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/17-rotation-lock.png | grep -q 99ede17594b30f04ed2904f7460335857e44f2d11a7335d4f4815ce76a0fef65
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
