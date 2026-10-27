#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console-usb/icons/icon.svg
# previous-hash: ca06cc37e2405f6a8f2f7e94cd1c396edc20b91e2453669d219b32c81b9b5f47
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg.nuxel-rollback.pre-v070-delta-release2 /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg.nuxel-rollback.pre-v070-delta-release2; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg.nuxel-staged
printf '%s  %s\n' ca06cc37e2405f6a8f2f7e94cd1c396edc20b91e2453669d219b32c81b9b5f47 /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-usb/icons/icon.svg | grep -q ca06cc37e2405f6a8f2f7e94cd1c396edc20b91e2453669d219b32c81b9b5f47
echo INSTALL-OK
