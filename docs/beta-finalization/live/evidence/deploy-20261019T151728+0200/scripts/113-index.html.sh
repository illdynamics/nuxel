#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/pwa/nuxel-home/index.html (service: nuxel-wayland, risk: high)
# staged source: pwa/nuxel-home/index.html
# previous-hash: e0235803cf94a3eaa0a74811e23a908aaf7c527eeff51b5aa4a68f13aec66940
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/index.html; systemctl restart nuxel-wayland; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged
printf '%s  %s\n' e0235803cf94a3eaa0a74811e23a908aaf7c527eeff51b5aa4a68f13aec66940 /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | grep -q e0235803cf94a3eaa0a74811e23a908aaf7c527eeff51b5aa4a68f13aec66940
systemctl restart nuxel-wayland
systemctl is-active nuxel-wayland
echo INSTALL-OK
