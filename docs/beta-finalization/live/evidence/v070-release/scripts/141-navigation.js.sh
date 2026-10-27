#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/navigation.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/navigation.js
# previous-hash: 8709890834b93ca2fd345d852f462ba22a4859f1df616c1c1cd3b222039ca4d7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/navigation.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/navigation.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/navigation.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/navigation.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/navigation.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/navigation.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/navigation.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/navigation.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/navigation.js /usr/share/nuxel/pwa/nuxel-home/js/navigation.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/navigation.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/navigation.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/navigation.js /usr/share/nuxel/pwa/nuxel-home/js/navigation.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/navigation.js.nuxel-staged
printf '%s  %s\n' 8709890834b93ca2fd345d852f462ba22a4859f1df616c1c1cd3b222039ca4d7 /usr/share/nuxel/pwa/nuxel-home/js/navigation.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/navigation.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/navigation.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/navigation.js | grep -q 8709890834b93ca2fd345d852f462ba22a4859f1df616c1c1cd3b222039ca4d7
echo INSTALL-OK
