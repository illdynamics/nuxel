#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-09_brightness.png
# previous-hash: 1ee93906798206de890686adb596caa10cb17a99796ecdb310823335534f44df
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png.nuxel-staged
printf '%s  %s\n' 1ee93906798206de890686adb596caa10cb17a99796ecdb310823335534f44df /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-09_brightness.png | grep -q 1ee93906798206de890686adb596caa10cb17a99796ecdb310823335534f44df
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
