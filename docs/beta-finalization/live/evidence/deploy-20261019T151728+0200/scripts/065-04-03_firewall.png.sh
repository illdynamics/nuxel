#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/04-03_firewall.png
# previous-hash: 27fa2a24d9c044dfb89c0cdd0d03c75499bd9c6de6cec62eeb6ede7916b82c5b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png.nuxel-staged
printf '%s  %s\n' 27fa2a24d9c044dfb89c0cdd0d03c75499bd9c6de6cec62eeb6ede7916b82c5b /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-03_firewall.png | grep -q 27fa2a24d9c044dfb89c0cdd0d03c75499bd9c6de6cec62eeb6ede7916b82c5b
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
