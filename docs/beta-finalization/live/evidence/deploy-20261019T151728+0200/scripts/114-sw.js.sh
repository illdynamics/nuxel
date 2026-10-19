#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/pwa/nuxel-home/sw.js (service: nuxel-wayland, risk: high)
# staged source: pwa/nuxel-home/sw.js
# previous-hash: 9f2b191a193906db774e82b3350c3717fafe2dcc0f87115626d6782067566325
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/sw.js; systemctl restart nuxel-wayland; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged
printf '%s  %s\n' 9f2b191a193906db774e82b3350c3717fafe2dcc0f87115626d6782067566325 /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | grep -q 9f2b191a193906db774e82b3350c3717fafe2dcc0f87115626d6782067566325
systemctl restart nuxel-wayland
systemctl is-active nuxel-wayland
echo INSTALL-OK
