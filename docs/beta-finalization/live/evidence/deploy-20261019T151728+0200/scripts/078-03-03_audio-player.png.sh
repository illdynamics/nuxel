#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-03_audio-player.png
# previous-hash: e5e0cfd404ba492c57bec2a5903c10cd44db02f0a7db0709b89cb2b65e37b3bc
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png.nuxel-staged
printf '%s  %s\n' e5e0cfd404ba492c57bec2a5903c10cd44db02f0a7db0709b89cb2b65e37b3bc /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-03_audio-player.png | grep -q e5e0cfd404ba492c57bec2a5903c10cd44db02f0a7db0709b89cb2b65e37b3bc
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
