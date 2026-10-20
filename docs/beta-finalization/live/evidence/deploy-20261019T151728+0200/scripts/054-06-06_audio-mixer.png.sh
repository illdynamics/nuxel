#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/06-06_audio-mixer.png
# previous-hash: 5808a5c03367a5a6a064259dfbc03d535fb10fad6241883d51b0319e37329730
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png.nuxel-staged
printf '%s  %s\n' 5808a5c03367a5a6a064259dfbc03d535fb10fad6241883d51b0319e37329730 /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-06_audio-mixer.png | grep -q 5808a5c03367a5a6a064259dfbc03d535fb10fad6241883d51b0319e37329730
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
