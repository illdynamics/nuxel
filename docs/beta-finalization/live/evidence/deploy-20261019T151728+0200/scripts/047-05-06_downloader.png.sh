#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/05-06_downloader.png
# previous-hash: c4d8c1594528b1eaa35a7b222a73ddc13c4ca08c972785f9a0cdee089cc31ba3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png.nuxel-staged
printf '%s  %s\n' c4d8c1594528b1eaa35a7b222a73ddc13c4ca08c972785f9a0cdee089cc31ba3 /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-06_downloader.png | grep -q c4d8c1594528b1eaa35a7b222a73ddc13c4ca08c972785f9a0cdee089cc31ba3
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
