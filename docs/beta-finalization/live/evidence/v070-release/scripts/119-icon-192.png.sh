#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/icons/icon-192.png
# previous-hash: e78e81d831cb310d1c4361ef07830b6f4aaca330c0b60aa12e798bdbb02f646e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png.nuxel-staged
printf '%s  %s\n' e78e81d831cb310d1c4361ef07830b6f4aaca330c0b60aa12e798bdbb02f646e /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-192.png | grep -q e78e81d831cb310d1c4361ef07830b6f4aaca330c0b60aa12e798bdbb02f646e
echo INSTALL-OK
