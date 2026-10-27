#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/css/home-settings.css
# previous-hash: cdc435a3ad3857745587fd3507930d3eefc88074949e696742bf6f0bea92df2f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css.nuxel-staged
printf '%s  %s\n' cdc435a3ad3857745587fd3507930d3eefc88074949e696742bf6f0bea92df2f /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/home-settings.css | grep -q cdc435a3ad3857745587fd3507930d3eefc88074949e696742bf6f0bea92df2f
echo INSTALL-OK
