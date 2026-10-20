#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-04_video-player.png
# previous-hash: 01954277879f9431c81abf9bca5ccec548e6a1deb9fa971b3c3dfb836252a218
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png.nuxel-staged
printf '%s  %s\n' 01954277879f9431c81abf9bca5ccec548e6a1deb9fa971b3c3dfb836252a218 /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-04_video-player.png | grep -q 01954277879f9431c81abf9bca5ccec548e6a1deb9fa971b3c3dfb836252a218
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
