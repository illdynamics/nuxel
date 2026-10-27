#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/icons/icon.svg
# previous-hash: 63fce7256bcf6b1f761eae5b2e401d99e6bbdd5dfbe1694844bcb42a0caf89a5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg.nuxel-staged
printf '%s  %s\n' 63fce7256bcf6b1f761eae5b2e401d99e6bbdd5dfbe1694844bcb42a0caf89a5 /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon.svg | grep -q 63fce7256bcf6b1f761eae5b2e401d99e6bbdd5dfbe1694844bcb42a0caf89a5
echo INSTALL-OK
