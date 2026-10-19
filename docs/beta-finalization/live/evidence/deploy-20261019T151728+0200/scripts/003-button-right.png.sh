#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/button-right.png (service: None, risk: high)
# staged source: assets/button-right.png
# previous-hash: 23257499b1617e95afd9b02a1bd99c86633f13e9f1f83d781b315d94873ee921
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/button-right.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/button-right.png.nuxel-rollback /usr/share/nuxel/assets/button-right.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/button-right.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/button-right.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/button-right.png)"
if [ -e /usr/share/nuxel/assets/button-right.png ] && [ ! -e /usr/share/nuxel/assets/button-right.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/button-right.png /usr/share/nuxel/assets/button-right.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/button-right.png.nuxel-staged
printf '%s  %s\n' 23257499b1617e95afd9b02a1bd99c86633f13e9f1f83d781b315d94873ee921 /usr/share/nuxel/assets/button-right.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/button-right.png.nuxel-staged /usr/share/nuxel/assets/button-right.png
sha256sum /usr/share/nuxel/assets/button-right.png | grep -q 23257499b1617e95afd9b02a1bd99c86633f13e9f1f83d781b315d94873ee921
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
