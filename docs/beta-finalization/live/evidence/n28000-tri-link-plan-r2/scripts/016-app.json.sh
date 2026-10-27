#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console-usb/app.json
# previous-hash: 70647d22da9817c8ba4aa1e071bc815da9e2523259e09814ccccac2d84ffcdbf
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json.nuxel-rollback.pre-deploy-20261027T164310-2129080 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json.nuxel-rollback.pre-deploy-20261027T164310-2129080 /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json.nuxel-rollback.pre-deploy-20261027T164310-2129080 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json.nuxel-rollback.pre-deploy-20261027T164310-2129080; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json.nuxel-staged
printf '%s  %s\n' 70647d22da9817c8ba4aa1e071bc815da9e2523259e09814ccccac2d84ffcdbf /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-usb/app.json | grep -q 70647d22da9817c8ba4aa1e071bc815da9e2523259e09814ccccac2d84ffcdbf
echo INSTALL-OK
