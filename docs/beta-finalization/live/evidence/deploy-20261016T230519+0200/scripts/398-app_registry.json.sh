#!/bin/sh
# app registry consumers/entries + verifiers -> /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json (service: nuxel-web, risk: low)
# staged source: shell/nuxel-home-native/nuxel_home/app_registry.json
# previous-hash: 11cc731bd1c3ad45e82eccb0733f7f34e41cb6a42bd06b857f6161cf48f533ee
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json)"
if [ -e /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json ] && [ ! -e /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json.nuxel-staged
printf '%s  %s\n' 11cc731bd1c3ad45e82eccb0733f7f34e41cb6a42bd06b857f6161cf48f533ee /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json.nuxel-staged /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json
sha256sum /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json | grep -q 11cc731bd1c3ad45e82eccb0733f7f34e41cb6a42bd06b857f6161cf48f533ee
systemctl restart nuxel-web
systemctl is-active nuxel-web
python3 -c "import json;a=json.load(open('/etc/nuxel/app-registry/app_registry.json'));assert a['registry_version']>=4" && test -x /usr/local/bin/verify-app-registry.py
echo INSTALL-OK
