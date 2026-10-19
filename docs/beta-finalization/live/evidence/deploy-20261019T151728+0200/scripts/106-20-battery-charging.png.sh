#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/20-battery-charging.png
# previous-hash: 3f0769393cc1c414b9ac5eb2fe186b8664bf5c20892721417972ab5ef3b48f01
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png.nuxel-staged
printf '%s  %s\n' 3f0769393cc1c414b9ac5eb2fe186b8664bf5c20892721417972ab5ef3b48f01 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/20-battery-charging.png | grep -q 3f0769393cc1c414b9ac5eb2fe186b8664bf5c20892721417972ab5ef3b48f01
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
