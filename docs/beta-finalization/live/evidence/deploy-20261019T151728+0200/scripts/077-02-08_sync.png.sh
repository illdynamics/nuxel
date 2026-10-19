#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/02-08_sync.png
# previous-hash: 9aa5f82017e3103ccb2c4d6c40bc86d5e4f93fe38c0048f76406a76b788ce109
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png.nuxel-staged
printf '%s  %s\n' 9aa5f82017e3103ccb2c4d6c40bc86d5e4f93fe38c0048f76406a76b788ce109 /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-08_sync.png | grep -q 9aa5f82017e3103ccb2c4d6c40bc86d5e4f93fe38c0048f76406a76b788ce109
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
