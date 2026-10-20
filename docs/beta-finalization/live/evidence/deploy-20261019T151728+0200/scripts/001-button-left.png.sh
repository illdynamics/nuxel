#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/button-left.png (service: None, risk: high)
# staged source: assets/button-left.png
# previous-hash: 3cc3c77a073788b5ee6192af7bbe5c970c971c68146e4c17ef404b246cc62b6a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/button-left.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/button-left.png.nuxel-rollback /usr/share/nuxel/assets/button-left.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/button-left.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/button-left.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/button-left.png)"
if [ -e /usr/share/nuxel/assets/button-left.png ] && [ ! -e /usr/share/nuxel/assets/button-left.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/button-left.png /usr/share/nuxel/assets/button-left.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/button-left.png.nuxel-staged
printf '%s  %s\n' 3cc3c77a073788b5ee6192af7bbe5c970c971c68146e4c17ef404b246cc62b6a /usr/share/nuxel/assets/button-left.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/button-left.png.nuxel-staged /usr/share/nuxel/assets/button-left.png
sha256sum /usr/share/nuxel/assets/button-left.png | grep -q 3cc3c77a073788b5ee6192af7bbe5c970c971c68146e4c17ef404b246cc62b6a
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
