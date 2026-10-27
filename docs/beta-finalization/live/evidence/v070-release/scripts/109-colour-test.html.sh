#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/colour-test.html (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/colour-test.html
# previous-hash: 1a1f15416829c1c8194ca6c638924156420104ac11095dd94458903b6dba574d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/colour-test.html.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/colour-test.html.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/colour-test.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/colour-test.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/colour-test.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/colour-test.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/colour-test.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/colour-test.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/colour-test.html /usr/share/nuxel/pwa/nuxel-home/colour-test.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/colour-test.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/colour-test.html.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/colour-test.html /usr/share/nuxel/pwa/nuxel-home/colour-test.html.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/colour-test.html.nuxel-staged
printf '%s  %s\n' 1a1f15416829c1c8194ca6c638924156420104ac11095dd94458903b6dba574d /usr/share/nuxel/pwa/nuxel-home/colour-test.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/colour-test.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/colour-test.html
sha256sum /usr/share/nuxel/pwa/nuxel-home/colour-test.html | grep -q 1a1f15416829c1c8194ca6c638924156420104ac11095dd94458903b6dba574d
echo INSTALL-OK
