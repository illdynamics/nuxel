#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/01-08_phone.png
# previous-hash: ba6e3c4ab20e966adebd86a58bc5e55d0dda7975e0d0ba6be0d80cf4c08ad93d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png.nuxel-staged
printf '%s  %s\n' ba6e3c4ab20e966adebd86a58bc5e55d0dda7975e0d0ba6be0d80cf4c08ad93d /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-08_phone.png | grep -q ba6e3c4ab20e966adebd86a58bc5e55d0dda7975e0d0ba6be0d80cf4c08ad93d
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
