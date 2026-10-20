#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png
# previous-hash: 1e53bd1b1ee385a51d897a2c49b370ce7f2442b9541f7b745441aa3927926fdf
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png.nuxel-staged
printf '%s  %s\n' 1e53bd1b1ee385a51d897a2c49b370ce7f2442b9541f7b745441aa3927926fdf /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/11-do-not-disturb.png | grep -q 1e53bd1b1ee385a51d897a2c49b370ce7f2442b9541f7b745441aa3927926fdf
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
