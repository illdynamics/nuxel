#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/nuxel-bottom-bar.jpg
# previous-hash: e40c6b64e828fd6bf5e7ff4c9fecd63c6404fb4ccea84716f361b62dcc0db984
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg.nuxel-staged
printf '%s  %s\n' e40c6b64e828fd6bf5e7ff4c9fecd63c6404fb4ccea84716f361b62dcc0db984 /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg | grep -q e40c6b64e828fd6bf5e7ff4c9fecd63c6404fb4ccea84716f361b62dcc0db984
echo INSTALL-OK
