#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/css/launcher.css (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/css/launcher.css
# previous-hash: 9d56a005af3bf09e0c31d1869b7c34f071b285676a3cd7184371dd1de18573e3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/css/launcher.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/launcher.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/launcher.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/launcher.css /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/launcher.css /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged
printf '%s  %s\n' 9d56a005af3bf09e0c31d1869b7c34f071b285676a3cd7184371dd1de18573e3 /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/launcher.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/launcher.css | grep -q 9d56a005af3bf09e0c31d1869b7c34f071b285676a3cd7184371dd1de18573e3
echo INSTALL-OK
