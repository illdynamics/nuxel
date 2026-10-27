#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console/icons/icon-96.png
# previous-hash: 4e2cae66544e076e982f09d4589cb5ffcb316c79c383efc5697b25e89347801f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png.nuxel-staged
printf '%s  %s\n' 4e2cae66544e076e982f09d4589cb5ffcb316c79c383efc5697b25e89347801f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-96.png | grep -q 4e2cae66544e076e982f09d4589cb5ffcb316c79c383efc5697b25e89347801f
echo INSTALL-OK
