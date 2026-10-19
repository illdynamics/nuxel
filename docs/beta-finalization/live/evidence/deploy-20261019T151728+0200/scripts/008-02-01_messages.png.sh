#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/02-01_messages.png
# previous-hash: fe1f515772eafbe77f401791564ac501da23b9662576f01d5417c2fd00c4b347
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png.nuxel-staged
printf '%s  %s\n' fe1f515772eafbe77f401791564ac501da23b9662576f01d5417c2fd00c4b347 /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-01_messages.png | grep -q fe1f515772eafbe77f401791564ac501da23b9662576f01d5417c2fd00c4b347
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
