#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/27-screen-record.png
# previous-hash: b0e9a4f6375f6c8b07bab76f6aaf3801da674f8667151a21343447dcbd7ec412
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png.nuxel-staged
printf '%s  %s\n' b0e9a4f6375f6c8b07bab76f6aaf3801da674f8667151a21343447dcbd7ec412 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/27-screen-record.png | grep -q b0e9a4f6375f6c8b07bab76f6aaf3801da674f8667151a21343447dcbd7ec412
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
