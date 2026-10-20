#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/21-sync.png
# previous-hash: 22487f70ae9a09dcd483801aa7a3ccbbb0fe1a870ce7b4553e85148350e3a195
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png.nuxel-staged
printf '%s  %s\n' 22487f70ae9a09dcd483801aa7a3ccbbb0fe1a870ce7b4553e85148350e3a195 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/21-sync.png | grep -q 22487f70ae9a09dcd483801aa7a3ccbbb0fe1a870ce7b4553e85148350e3a195
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
