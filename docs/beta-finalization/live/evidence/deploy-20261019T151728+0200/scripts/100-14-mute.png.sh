#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/14-mute.png
# previous-hash: 6cbac20323ea70c7e7f090305188ff83d0925ac753df06ec820643413afe3287
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png.nuxel-staged
printf '%s  %s\n' 6cbac20323ea70c7e7f090305188ff83d0925ac753df06ec820643413afe3287 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/14-mute.png | grep -q 6cbac20323ea70c7e7f090305188ff83d0925ac753df06ec820643413afe3287
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
