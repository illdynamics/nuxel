#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/sw.js.a59-bak
# previous-hash: 62121464e759b385aa13b61fb0e745f8c3a810b65bab6b814fb709cfc13ad055
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak.nuxel-staged
printf '%s  %s\n' 62121464e759b385aa13b61fb0e745f8c3a810b65bab6b814fb709cfc13ad055 /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak
sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js.a59-bak | grep -q 62121464e759b385aa13b61fb0e745f8c3a810b65bab6b814fb709cfc13ad055
echo INSTALL-OK
