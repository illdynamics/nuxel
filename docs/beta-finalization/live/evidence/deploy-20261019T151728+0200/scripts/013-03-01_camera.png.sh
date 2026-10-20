#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-01_camera.png
# previous-hash: 89fa0c84db76ca083a51c882a562d78881f200651b050a2f377b00e045de5af1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png.nuxel-staged
printf '%s  %s\n' 89fa0c84db76ca083a51c882a562d78881f200651b050a2f377b00e045de5af1 /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-01_camera.png | grep -q 89fa0c84db76ca083a51c882a562d78881f200651b050a2f377b00e045de5af1
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
