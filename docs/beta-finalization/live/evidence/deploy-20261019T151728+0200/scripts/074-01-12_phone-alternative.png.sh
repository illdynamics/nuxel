#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/01-12_phone-alternative.png
# previous-hash: 76a730c35c6cdfdc6b6a636c9db357261626247d0cf959b723ffdbb17ba48f90
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png.nuxel-staged
printf '%s  %s\n' 76a730c35c6cdfdc6b6a636c9db357261626247d0cf959b723ffdbb17ba48f90 /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png | grep -q 76a730c35c6cdfdc6b6a636c9db357261626247d0cf959b723ffdbb17ba48f90
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
