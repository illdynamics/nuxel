#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/01-10_document.png
# previous-hash: 8c2d8c73a2143c728176ada52243f2055985a941bf104c57ffaa621391d2cc67
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png.nuxel-staged
printf '%s  %s\n' 8c2d8c73a2143c728176ada52243f2055985a941bf104c57ffaa621391d2cc67 /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-10_document.png | grep -q 8c2d8c73a2143c728176ada52243f2055985a941bf104c57ffaa621391d2cc67
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
