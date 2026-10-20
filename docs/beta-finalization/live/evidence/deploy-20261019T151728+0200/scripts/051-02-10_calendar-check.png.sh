#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/02-10_calendar-check.png
# previous-hash: 2b165c23bf7ccd794c70f87b468ecb648ebf6bad40e1554dac1f32ea6e15b86b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png.nuxel-staged
printf '%s  %s\n' 2b165c23bf7ccd794c70f87b468ecb648ebf6bad40e1554dac1f32ea6e15b86b /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-10_calendar-check.png | grep -q 2b165c23bf7ccd794c70f87b468ecb648ebf6bad40e1554dac1f32ea6e15b86b
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
