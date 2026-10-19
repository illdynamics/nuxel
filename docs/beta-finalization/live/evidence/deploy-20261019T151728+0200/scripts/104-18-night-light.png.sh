#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/18-night-light.png
# previous-hash: f185f1a7ff1bb9bba40cc720e1b4ff43b846aa6a42bb74d15875311c2194cc40
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png.nuxel-staged
printf '%s  %s\n' f185f1a7ff1bb9bba40cc720e1b4ff43b846aa6a42bb74d15875311c2194cc40 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/18-night-light.png | grep -q f185f1a7ff1bb9bba40cc720e1b4ff43b846aa6a42bb74d15875311c2194cc40
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
