#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png
# previous-hash: cb2f2746a23c5fed3b270cdced2a628316e64141c6e1dd8cd9f9212bd8272851
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-staged
printf '%s  %s\n' cb2f2746a23c5fed3b270cdced2a628316e64141c6e1dd8cd9f9212bd8272851 /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-01_root-sudo-control.png | grep -q cb2f2746a23c5fed3b270cdced2a628316e64141c6e1dd8cd9f9212bd8272851
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
