#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png
# previous-hash: 8ee25e68c26a4453d62972f3713e015e97afa987ba6766f4e9374544610d6791
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png.nuxel-staged
printf '%s  %s\n' 8ee25e68c26a4453d62972f3713e015e97afa987ba6766f4e9374544610d6791 /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-12_linux-tux-alternative.png | grep -q 8ee25e68c26a4453d62972f3713e015e97afa987ba6766f4e9374544610d6791
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
