#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/icons/icon-512.png
# previous-hash: 3f72dea12870fe315349d24aac0326fb1352f38756682253b99a9276f0da248f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-staged
printf '%s  %s\n' 3f72dea12870fe315349d24aac0326fb1352f38756682253b99a9276f0da248f /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png | grep -q 3f72dea12870fe315349d24aac0326fb1352f38756682253b99a9276f0da248f
echo INSTALL-OK
