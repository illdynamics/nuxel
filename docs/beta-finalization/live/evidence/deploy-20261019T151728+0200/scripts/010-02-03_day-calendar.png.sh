#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/02-03_day-calendar.png
# previous-hash: e4460c41e03c82c51b95eda2e04e569588b61068e0e90977759249d58c1e4016
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png.nuxel-staged
printf '%s  %s\n' e4460c41e03c82c51b95eda2e04e569588b61068e0e90977759249d58c1e4016 /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-03_day-calendar.png | grep -q e4460c41e03c82c51b95eda2e04e569588b61068e0e90977759249d58c1e4016
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
