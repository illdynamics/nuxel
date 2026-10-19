#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png
# previous-hash: 6851c02f64f044fdbd99531d5367ffc791f97993ed4b3e3b639f6f692c694e6a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png.nuxel-staged
printf '%s  %s\n' 6851c02f64f044fdbd99531d5367ffc791f97993ed4b3e3b639f6f692c694e6a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-01_tor-privacy-tool.png | grep -q 6851c02f64f044fdbd99531d5367ffc791f97993ed4b3e3b639f6f692c694e6a
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
