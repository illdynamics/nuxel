#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/libexec/nuxel/nuxel-sound-cue (service: None, risk: high)
# staged source: tools/s10plus/a33/nuxel-sound-cue.py
# previous-hash: 4b23eeec037b966a9bc56be0c7a855eeb414e6c87ed5ce87593c13dc2f550cef
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/libexec/nuxel/nuxel-sound-cue.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-sound-cue.nuxel-rollback /usr/libexec/nuxel/nuxel-sound-cue; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/libexec/nuxel/nuxel-sound-cue ]; then printf 'PREV=%s\n' "$(sha256sum /usr/libexec/nuxel/nuxel-sound-cue | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/libexec/nuxel/nuxel-sound-cue)"
if [ -e /usr/libexec/nuxel/nuxel-sound-cue ] && [ ! -e /usr/libexec/nuxel/nuxel-sound-cue.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-sound-cue /usr/libexec/nuxel/nuxel-sound-cue.nuxel-rollback; fi
test -f /usr/libexec/nuxel/nuxel-sound-cue.nuxel-staged
printf '%s  %s\n' 4b23eeec037b966a9bc56be0c7a855eeb414e6c87ed5ce87593c13dc2f550cef /usr/libexec/nuxel/nuxel-sound-cue.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/libexec/nuxel/nuxel-sound-cue.nuxel-staged /usr/libexec/nuxel/nuxel-sound-cue
sha256sum /usr/libexec/nuxel/nuxel-sound-cue | grep -q 4b23eeec037b966a9bc56be0c7a855eeb414e6c87ed5ce87593c13dc2f550cef
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
