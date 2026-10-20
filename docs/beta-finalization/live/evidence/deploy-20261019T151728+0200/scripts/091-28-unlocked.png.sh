#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/28-unlocked.png
# previous-hash: 292a546ce7f0fdc7fe5861b2288143247aa3b9b6fd0b371a032cf33b89b9cac3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png.nuxel-staged
printf '%s  %s\n' 292a546ce7f0fdc7fe5861b2288143247aa3b9b6fd0b371a032cf33b89b9cac3 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/28-unlocked.png | grep -q 292a546ce7f0fdc7fe5861b2288143247aa3b9b6fd0b371a032cf33b89b9cac3
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
