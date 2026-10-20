#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png
# previous-hash: db5825066b92cb6cf5924c7fc2e9f536ebf81159b0f40a1aded23d0efb7defdb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png.nuxel-staged
printf '%s  %s\n' db5825066b92cb6cf5924c7fc2e9f536ebf81159b0f40a1aded23d0efb7defdb /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/03-airplane-mode.png | grep -q db5825066b92cb6cf5924c7fc2e9f536ebf81159b0f40a1aded23d0efb7defdb
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
