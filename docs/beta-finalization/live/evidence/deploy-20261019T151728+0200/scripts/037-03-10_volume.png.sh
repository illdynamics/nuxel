#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-10_volume.png
# previous-hash: 305639f42b9b749d964ef7dd932e984548f78ecb9a5e7b15f3cb39b9f2c437b9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png.nuxel-staged
printf '%s  %s\n' 305639f42b9b749d964ef7dd932e984548f78ecb9a5e7b15f3cb39b9f2c437b9 /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-10_volume.png | grep -q 305639f42b9b749d964ef7dd932e984548f78ecb9a5e7b15f3cb39b9f2c437b9
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
