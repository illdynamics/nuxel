#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/04-08_information.png
# previous-hash: e1532f547f0e1c2b896c530c314066c07128bc800c31b0e79c8842abcdfbc8b9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png.nuxel-staged
printf '%s  %s\n' e1532f547f0e1c2b896c530c314066c07128bc800c31b0e79c8842abcdfbc8b9 /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-08_information.png | grep -q e1532f547f0e1c2b896c530c314066c07128bc800c31b0e79c8842abcdfbc8b9
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
