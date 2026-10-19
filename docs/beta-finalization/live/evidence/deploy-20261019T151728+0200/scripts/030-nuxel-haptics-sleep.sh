#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/libexec/nuxel/nuxel-haptics-sleep (service: None, risk: high)
# staged source: services/nuxel-haptics/nuxel-haptics-sleep
# previous-hash: 83ef618ffffda6b96cc5b959dd9e4553f666671fd7c48b169dcbe45399e92177
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/libexec/nuxel/nuxel-haptics-sleep.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-haptics-sleep.nuxel-rollback /usr/libexec/nuxel/nuxel-haptics-sleep; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/libexec/nuxel/nuxel-haptics-sleep ]; then printf 'PREV=%s\n' "$(sha256sum /usr/libexec/nuxel/nuxel-haptics-sleep | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/libexec/nuxel/nuxel-haptics-sleep)"
if [ -e /usr/libexec/nuxel/nuxel-haptics-sleep ] && [ ! -e /usr/libexec/nuxel/nuxel-haptics-sleep.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-haptics-sleep /usr/libexec/nuxel/nuxel-haptics-sleep.nuxel-rollback; fi
test -f /usr/libexec/nuxel/nuxel-haptics-sleep.nuxel-staged
printf '%s  %s\n' 83ef618ffffda6b96cc5b959dd9e4553f666671fd7c48b169dcbe45399e92177 /usr/libexec/nuxel/nuxel-haptics-sleep.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/libexec/nuxel/nuxel-haptics-sleep.nuxel-staged /usr/libexec/nuxel/nuxel-haptics-sleep
sha256sum /usr/libexec/nuxel/nuxel-haptics-sleep | grep -q 83ef618ffffda6b96cc5b959dd9e4553f666671fd7c48b169dcbe45399e92177
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
