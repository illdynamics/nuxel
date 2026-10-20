#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/05-07_web-window.png
# previous-hash: 77b5e77bbbf5111ffe07f64f81dd8f8846af998ba38b265f826d6b258642e6b6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png.nuxel-staged
printf '%s  %s\n' 77b5e77bbbf5111ffe07f64f81dd8f8846af998ba38b265f826d6b258642e6b6 /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-07_web-window.png | grep -q 77b5e77bbbf5111ffe07f64f81dd8f8846af998ba38b265f826d6b258642e6b6
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
