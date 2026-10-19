#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-12_settings-alternative.png
# previous-hash: 1aaad3699b8ef7481852786734372e7ca5d3e0ccec94d8ee66da62201d6c9f9e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png.nuxel-staged
printf '%s  %s\n' 1aaad3699b8ef7481852786734372e7ca5d3e0ccec94d8ee66da62201d6c9f9e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-12_settings-alternative.png | grep -q 1aaad3699b8ef7481852786734372e7ca5d3e0ccec94d8ee66da62201d6c9f9e
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
