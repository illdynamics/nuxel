#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/pwa/nuxel-home/js/apps.js (service: nuxel-wayland, risk: high)
# staged source: pwa/nuxel-home/js/apps.js
# previous-hash: cae8d99447cbbbbcc90b00a9c715307ff3d20e56e98ede0374341cc4448c2890
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/apps.js; systemctl restart nuxel-wayland; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/apps.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/apps.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged
printf '%s  %s\n' cae8d99447cbbbbcc90b00a9c715307ff3d20e56e98ede0374341cc4448c2890 /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/apps.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/apps.js | grep -q cae8d99447cbbbbcc90b00a9c715307ff3d20e56e98ede0374341cc4448c2890
systemctl restart nuxel-wayland
systemctl is-active nuxel-wayland
echo INSTALL-OK
