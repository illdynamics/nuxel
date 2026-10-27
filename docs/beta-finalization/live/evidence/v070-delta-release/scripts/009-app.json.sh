#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/app.json (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/app.json
# previous-hash: bc5da102e414875cfb7f4154f9dd1fcf5328b8383e218a5ab08699eb9c0eda8c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback.pre-v070-delta-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback.pre-v070-delta-release /usr/share/nuxel/pwa/nuxel-apps/settings/app.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/app.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/app.json /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback.pre-v070-delta-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/app.json /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback.pre-v070-delta-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-staged
printf '%s  %s\n' bc5da102e414875cfb7f4154f9dd1fcf5328b8383e218a5ab08699eb9c0eda8c /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/app.json | grep -q bc5da102e414875cfb7f4154f9dd1fcf5328b8383e218a5ab08699eb9c0eda8c
echo INSTALL-OK
