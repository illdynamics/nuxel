#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/06-08_workspace.png
# previous-hash: adb3a8e45a37ea7409448f17bc2b2fa972690da9b593391a1b5bb706b2a72a8b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png.nuxel-staged
printf '%s  %s\n' adb3a8e45a37ea7409448f17bc2b2fa972690da9b593391a1b5bb706b2a72a8b /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-08_workspace.png | grep -q adb3a8e45a37ea7409448f17bc2b2fa972690da9b593391a1b5bb706b2a72a8b
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
