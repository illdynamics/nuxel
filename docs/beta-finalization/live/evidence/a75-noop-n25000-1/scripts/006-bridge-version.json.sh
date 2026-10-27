#!/bin/sh
# systemd unit env pins + bridge-version.json + shared PWA bridge honesty fallback -> /usr/share/nuxel/pwa/nuxel-common/bridge-version.json (service: None, risk: medium)
# staged source: pwa/nuxel-common/bridge-version.json
# previous-hash: 4d9710dd847789380761c118185c84d5593ed9c829f4a852402780f5ec3876de
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-a75-noop-n25000-1 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-a75-noop-n25000-1 /usr/share/nuxel/pwa/nuxel-common/bridge-version.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge-version.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/bridge-version.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-a75-noop-n25000-1 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-a75-noop-n25000-1; fi
test -f /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged
printf '%s  %s\n' 4d9710dd847789380761c118185c84d5593ed9c829f4a852402780f5ec3876de /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/bridge-version.json
sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge-version.json | grep -q 4d9710dd847789380761c118185c84d5593ed9c829f4a852402780f5ec3876de
echo INSTALL-OK
