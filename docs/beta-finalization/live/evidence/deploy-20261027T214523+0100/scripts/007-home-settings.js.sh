#!/bin/sh
# v0.7.1-beta PWA version pins and launcher cache namespace -> /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/home-settings.js
# previous-hash: 2a1dffa724ff5c05d87b0a86a4f230b639f3d4338aaa2b0478a72715b0163190
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T214523-2399095 /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T214523-2399095; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-staged
printf '%s  %s\n' 2a1dffa724ff5c05d87b0a86a4f230b639f3d4338aaa2b0478a72715b0163190 /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js | grep -q 2a1dffa724ff5c05d87b0a86a4f230b639f3d4338aaa2b0478a72715b0163190
echo INSTALL-OK
