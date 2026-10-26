#!/bin/sh
# systemd unit env pins + bridge-version.json + shared PWA bridge honesty fallback -> /usr/share/nuxel/pwa/nuxel-common/bridge-version.json (service: None, risk: medium)
# staged source: pwa/nuxel-common/bridge-version.json
# previous-hash: b17a96a2851bae442d07925b8fb184970e49564c4659165565dd219f62c33fca
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-common/bridge-version.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge-version.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/bridge-version.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged
printf '%s  %s\n' b17a96a2851bae442d07925b8fb184970e49564c4659165565dd219f62c33fca /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/bridge-version.json
sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge-version.json | grep -q b17a96a2851bae442d07925b8fb184970e49564c4659165565dd219f62c33fca
( systemctl daemon-reload && (systemctl restart nuxel-bridge.service nuxel-http-bridge.service || true) ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
