#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/07-tor.png
# previous-hash: 6e8da052c5c5544b0bd686648fb01514de4792604b5c08c559d0d4437c5209be
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png.nuxel-staged
printf '%s  %s\n' 6e8da052c5c5544b0bd686648fb01514de4792604b5c08c559d0d4437c5209be /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/07-tor.png | grep -q 6e8da052c5c5544b0bd686648fb01514de4792604b5c08c559d0d4437c5209be
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
