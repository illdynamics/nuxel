#!/bin/sh
# v0.7.1-beta PWA version pins and launcher cache namespace -> /usr/share/nuxel/pwa/nuxel-home/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/sw.js
# previous-hash: b063da78e324cb761da966be80843f578d0bdd88db3252643255faee6643566b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T214523-2399095 /usr/share/nuxel/pwa/nuxel-home/sw.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T214523-2399095; fi
test -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged
printf '%s  %s\n' b063da78e324cb761da966be80843f578d0bdd88db3252643255faee6643566b /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | grep -q b063da78e324cb761da966be80843f578d0bdd88db3252643255faee6643566b
echo INSTALL-OK
