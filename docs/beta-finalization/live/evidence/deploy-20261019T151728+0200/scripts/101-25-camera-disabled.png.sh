#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png
# previous-hash: 0132c48a500a58155e02eae329d9f6fa528c200ed44ecfbd834803f8e0b909e5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png.nuxel-staged
printf '%s  %s\n' 0132c48a500a58155e02eae329d9f6fa528c200ed44ecfbd834803f8e0b909e5 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/25-camera-disabled.png | grep -q 0132c48a500a58155e02eae329d9f6fa528c200ed44ecfbd834803f8e0b909e5
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
