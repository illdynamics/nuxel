#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png
# previous-hash: ca435e6e2c540531aa184f57de4cdb9cd9f9ae211c72ddd67ddc05036d94c595
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png.nuxel-staged
printf '%s  %s\n' ca435e6e2c540531aa184f57de4cdb9cd9f9ae211c72ddd67ddc05036d94c595 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/16-adaptive-brightness.png | grep -q ca435e6e2c540531aa184f57de4cdb9cd9f9ae211c72ddd67ddc05036d94c595
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
