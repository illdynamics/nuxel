#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/.keep (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/.keep
# previous-hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/.keep.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/.keep.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-apps/settings/.keep; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/.keep ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/.keep | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/.keep)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/.keep ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/.keep.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/.keep /usr/share/nuxel/pwa/nuxel-apps/settings/.keep.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/.keep ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/.keep.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/.keep /usr/share/nuxel/pwa/nuxel-apps/settings/.keep.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/.keep.nuxel-staged
printf '%s  %s\n' e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 /usr/share/nuxel/pwa/nuxel-apps/settings/.keep.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/.keep.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/.keep
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/.keep | grep -q e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
echo INSTALL-OK
