#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/maps/css/maps.css
# previous-hash: 803c933290da3f3cd7c6a74e1d7f00b7a478d29e8923b495aa06d86153582ebb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback.pre-v070-delta-release3 /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback.pre-v070-delta-release3; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-staged
printf '%s  %s\n' 803c933290da3f3cd7c6a74e1d7f00b7a478d29e8923b495aa06d86153582ebb /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css | grep -q 803c933290da3f3cd7c6a74e1d7f00b7a478d29e8923b495aa06d86153582ebb
echo INSTALL-OK
