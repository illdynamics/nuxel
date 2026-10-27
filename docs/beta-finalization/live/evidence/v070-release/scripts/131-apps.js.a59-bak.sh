#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/apps.js.a59-bak
# previous-hash: c6a72cc0292ea145f59355ddc3dd70cf1640bf9752dbd9e3bee9ffab9a9f3e98
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak.nuxel-staged
printf '%s  %s\n' c6a72cc0292ea145f59355ddc3dd70cf1640bf9752dbd9e3bee9ffab9a9f3e98 /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/apps.js.a59-bak | grep -q c6a72cc0292ea145f59355ddc3dd70cf1640bf9752dbd9e3bee9ffab9a9f3e98
echo INSTALL-OK
