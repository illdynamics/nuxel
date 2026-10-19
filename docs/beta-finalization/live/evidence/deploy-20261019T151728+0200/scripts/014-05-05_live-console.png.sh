#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/05-05_live-console.png
# previous-hash: c695dedd90d5025e33902e2e8ad5f072480084af8950f7c27f435399ac79e6c2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-staged
printf '%s  %s\n' c695dedd90d5025e33902e2e8ad5f072480084af8950f7c27f435399ac79e6c2 /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png | grep -q c695dedd90d5025e33902e2e8ad5f072480084af8950f7c27f435399ac79e6c2
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
