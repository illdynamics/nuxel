#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/01-wifi.png
# previous-hash: 588920a76e1b270dddcb0b853a7f55afb9ae21aeb9f4d488dcb50bcc4d086f2b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png.nuxel-staged
printf '%s  %s\n' 588920a76e1b270dddcb0b853a7f55afb9ae21aeb9f4d488dcb50bcc4d086f2b /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png | grep -q 588920a76e1b270dddcb0b853a7f55afb9ae21aeb9f4d488dcb50bcc4d086f2b
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
