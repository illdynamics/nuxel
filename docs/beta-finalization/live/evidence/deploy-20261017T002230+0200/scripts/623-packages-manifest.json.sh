#!/bin/sh
# Fedora 43 package set reconciliation (data + verifier) -> /usr/lib/nuxel/packages-manifest.json (service: None, risk: high)
# staged source: images/s10plus/packages-manifest.json
# previous-hash: 99f68383be024f8aeeeea4f3af7177df21969b2294edc0b6877da785c2dea7dc
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/packages-manifest.json.nuxel-rollback ]; then cp -a /usr/lib/nuxel/packages-manifest.json.nuxel-rollback /usr/lib/nuxel/packages-manifest.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/packages-manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/packages-manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/packages-manifest.json)"
if [ -e /usr/lib/nuxel/packages-manifest.json ] && [ ! -e /usr/lib/nuxel/packages-manifest.json.nuxel-rollback ]; then cp -a /usr/lib/nuxel/packages-manifest.json /usr/lib/nuxel/packages-manifest.json.nuxel-rollback; fi
test -f /usr/lib/nuxel/packages-manifest.json.nuxel-staged
printf '%s  %s\n' 99f68383be024f8aeeeea4f3af7177df21969b2294edc0b6877da785c2dea7dc /usr/lib/nuxel/packages-manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/packages-manifest.json.nuxel-staged /usr/lib/nuxel/packages-manifest.json
sha256sum /usr/lib/nuxel/packages-manifest.json | grep -q 99f68383be024f8aeeeea4f3af7177df21969b2294edc0b6877da785c2dea7dc
( python3 -c "import json;json.load(open('/usr/lib/nuxel/packages-manifest.json'))" ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
