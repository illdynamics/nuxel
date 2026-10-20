#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png
# previous-hash: 580ccd37d968447fe5cabadb95d923223a151799ccc98378aa7a5f17980b0a84
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png.nuxel-staged
printf '%s  %s\n' 580ccd37d968447fe5cabadb95d923223a151799ccc98378aa7a5f17980b0a84 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/24-microphone-muted.png | grep -q 580ccd37d968447fe5cabadb95d923223a151799ccc98378aa7a5f17980b0a84
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
