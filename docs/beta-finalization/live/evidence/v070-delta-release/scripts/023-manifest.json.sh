#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console-usb/manifest.json
# previous-hash: 9fb96ccd675e264d71e6489fce5d3ad3ba25a69a31783bc7774ca129b2071752
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json.nuxel-rollback.pre-v070-delta-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json.nuxel-rollback.pre-v070-delta-release /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json.nuxel-rollback.pre-v070-delta-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json.nuxel-rollback.pre-v070-delta-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json.nuxel-staged
printf '%s  %s\n' 9fb96ccd675e264d71e6489fce5d3ad3ba25a69a31783bc7774ca129b2071752 /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-usb/manifest.json | grep -q 9fb96ccd675e264d71e6489fce5d3ad3ba25a69a31783bc7774ca129b2071752
echo INSTALL-OK
