#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/12-volume.png
# previous-hash: 51b87b4999245c98085eaf7252d6546ef3c8f22c6ae46477d6bda1a6fed5dbc8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png.nuxel-staged
printf '%s  %s\n' 51b87b4999245c98085eaf7252d6546ef3c8f22c6ae46477d6bda1a6fed5dbc8 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/12-volume.png | grep -q 51b87b4999245c98085eaf7252d6546ef3c8f22c6ae46477d6bda1a6fed5dbc8
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
