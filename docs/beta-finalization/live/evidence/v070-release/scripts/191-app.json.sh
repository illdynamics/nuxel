#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/maps/app.json (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/maps/app.json
# previous-hash: be8f8cb5fdda78d7227de921b6c6ea4425ae60c00c122fd50bf311a631e78f57
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-apps/maps/app.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/app.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/app.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/app.json /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/app.json /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-staged
printf '%s  %s\n' be8f8cb5fdda78d7227de921b6c6ea4425ae60c00c122fd50bf311a631e78f57 /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/app.json | grep -q be8f8cb5fdda78d7227de921b6c6ea4425ae60c00c122fd50bf311a631e78f57
echo INSTALL-OK
