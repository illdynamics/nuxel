#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/sw.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/sw.js
# previous-hash: f45eea2d0fe59155cb2ca33a229b9328b4760ad5735b22176d0023b612af1fba
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-v070-delta-release2 /usr/share/nuxel/pwa/nuxel-home/sw.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-v070-delta-release2; fi
test -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged
printf '%s  %s\n' f45eea2d0fe59155cb2ca33a229b9328b4760ad5735b22176d0023b612af1fba /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | grep -q f45eea2d0fe59155cb2ca33a229b9328b4760ad5735b22176d0023b612af1fba
echo INSTALL-OK
