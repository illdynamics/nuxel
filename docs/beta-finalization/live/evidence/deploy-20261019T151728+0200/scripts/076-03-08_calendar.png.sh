#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-08_calendar.png
# previous-hash: e5bbc4b3a3ff3c284006211834c14ddcd0efe50191f93f0278778795cf353957
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png.nuxel-staged
printf '%s  %s\n' e5bbc4b3a3ff3c284006211834c14ddcd0efe50191f93f0278778795cf353957 /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-08_calendar.png | grep -q e5bbc4b3a3ff3c284006211834c14ddcd0efe50191f93f0278778795cf353957
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
