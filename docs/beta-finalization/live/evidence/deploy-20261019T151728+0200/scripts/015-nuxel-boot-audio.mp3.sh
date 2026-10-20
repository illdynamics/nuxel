#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-boot-audio.mp3 (service: None, risk: high)
# staged source: assets/nuxel-boot-audio.mp3
# previous-hash: cbacfcf706cf8e93dfa44c14cc7786c973d9af9995781243e2ae24cd6a178896
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-boot-audio.mp3.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-boot-audio.mp3.nuxel-rollback /usr/share/nuxel/assets/nuxel-boot-audio.mp3; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-boot-audio.mp3 ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-boot-audio.mp3 | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-boot-audio.mp3)"
if [ -e /usr/share/nuxel/assets/nuxel-boot-audio.mp3 ] && [ ! -e /usr/share/nuxel/assets/nuxel-boot-audio.mp3.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-boot-audio.mp3 /usr/share/nuxel/assets/nuxel-boot-audio.mp3.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-boot-audio.mp3.nuxel-staged
printf '%s  %s\n' cbacfcf706cf8e93dfa44c14cc7786c973d9af9995781243e2ae24cd6a178896 /usr/share/nuxel/assets/nuxel-boot-audio.mp3.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-boot-audio.mp3.nuxel-staged /usr/share/nuxel/assets/nuxel-boot-audio.mp3
sha256sum /usr/share/nuxel/assets/nuxel-boot-audio.mp3 | grep -q cbacfcf706cf8e93dfa44c14cc7786c973d9af9995781243e2ae24cd6a178896
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
