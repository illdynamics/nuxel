#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-07_vpn-protected.png
# previous-hash: 827ba4b125074f36eaf8c0a78660ed1fbfc422d38cb82696f8b88944d4fcc22a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png.nuxel-staged
printf '%s  %s\n' 827ba4b125074f36eaf8c0a78660ed1fbfc422d38cb82696f8b88944d4fcc22a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-07_vpn-protected.png | grep -q 827ba4b125074f36eaf8c0a78660ed1fbfc422d38cb82696f8b88944d4fcc22a
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
