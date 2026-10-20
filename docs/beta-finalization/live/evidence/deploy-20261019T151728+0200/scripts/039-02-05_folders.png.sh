#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/02-05_folders.png
# previous-hash: ee6562f1839ff3ac3bc6f88545cc3b7a6eb3dc7166bc625c88fd4371036d4e20
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png.nuxel-staged
printf '%s  %s\n' ee6562f1839ff3ac3bc6f88545cc3b7a6eb3dc7166bc625c88fd4371036d4e20 /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-05_folders.png | grep -q ee6562f1839ff3ac3bc6f88545cc3b7a6eb3dc7166bc625c88fd4371036d4e20
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
