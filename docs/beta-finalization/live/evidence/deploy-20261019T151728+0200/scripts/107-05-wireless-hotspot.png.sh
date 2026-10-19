#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png
# previous-hash: ec61cea3f63380aa202c3595f52f513542c6d212324232898daca19960b60c88
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png.nuxel-staged
printf '%s  %s\n' ec61cea3f63380aa202c3595f52f513542c6d212324232898daca19960b60c88 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/05-wireless-hotspot.png | grep -q ec61cea3f63380aa202c3595f52f513542c6d212324232898daca19960b60c88
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
