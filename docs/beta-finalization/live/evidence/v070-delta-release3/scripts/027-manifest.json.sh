#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console-wifi/manifest.json
# previous-hash: 06fc0389ebb8e75eccb7d813b6162932d804cdada0cc3c334fc88c85a96105a5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json.nuxel-rollback.pre-v070-delta-release3 /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json.nuxel-rollback.pre-v070-delta-release3; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json.nuxel-staged
printf '%s  %s\n' 06fc0389ebb8e75eccb7d813b6162932d804cdada0cc3c334fc88c85a96105a5 /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-wifi/manifest.json | grep -q 06fc0389ebb8e75eccb7d813b6162932d804cdada0cc3c334fc88c85a96105a5
echo INSTALL-OK
