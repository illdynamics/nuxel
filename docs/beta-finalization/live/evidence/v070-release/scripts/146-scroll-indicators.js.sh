#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/scroll-indicators.js
# previous-hash: a5d51cd76677f6ddb34b7d8782a5f5bbc17401dd615d5f372bdc3f600319b2c5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js.nuxel-staged
printf '%s  %s\n' a5d51cd76677f6ddb34b7d8782a5f5bbc17401dd615d5f372bdc3f600319b2c5 /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js | grep -q a5d51cd76677f6ddb34b7d8782a5f5bbc17401dd615d5f372bdc3f600319b2c5
echo INSTALL-OK
