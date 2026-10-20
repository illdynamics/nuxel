#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png
# previous-hash: 4a7a400228b625ca90823827de460f14cbd68c021a27f86b0894a1baa6461218
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png.nuxel-staged
printf '%s  %s\n' 4a7a400228b625ca90823827de460f14cbd68c021a27f86b0894a1baa6461218 /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-11_terminal-alternative.png | grep -q 4a7a400228b625ca90823827de460f14cbd68c021a27f86b0894a1baa6461218
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
