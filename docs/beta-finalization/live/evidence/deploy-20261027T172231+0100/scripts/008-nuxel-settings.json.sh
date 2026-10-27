#!/bin/sh
# first-party Settings capability grant (bluetooth:manage/scan) -> /var/lib/nuxel/permissions/nuxel-settings.json (service: nuxel-bridge, risk: medium)
# staged source: configs/nuxel/permissions/nuxel-settings.json
# previous-hash: dce7f242c18b5a56328b53d9c4a681141a3075298bd13030d463b5cfcadb77b8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /var/lib/nuxel/permissions/nuxel-settings.json.nuxel-rollback.pre-deploy-20261027T172231-2153662 ]; then cp -a /var/lib/nuxel/permissions/nuxel-settings.json.nuxel-rollback.pre-deploy-20261027T172231-2153662 /var/lib/nuxel/permissions/nuxel-settings.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -d /var/lib/nuxel/permissions
if [ -e /var/lib/nuxel/permissions/nuxel-settings.json ]; then printf 'PREV=%s\n' "$(sha256sum /var/lib/nuxel/permissions/nuxel-settings.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /var/lib/nuxel/permissions/nuxel-settings.json)"
if [ -e /var/lib/nuxel/permissions/nuxel-settings.json ] && [ ! -e /var/lib/nuxel/permissions/nuxel-settings.json.nuxel-rollback ]; then cp -a /var/lib/nuxel/permissions/nuxel-settings.json /var/lib/nuxel/permissions/nuxel-settings.json.nuxel-rollback; fi
if [ -e /var/lib/nuxel/permissions/nuxel-settings.json ] && [ ! -e /var/lib/nuxel/permissions/nuxel-settings.json.nuxel-rollback.pre-deploy-20261027T172231-2153662 ]; then cp -a /var/lib/nuxel/permissions/nuxel-settings.json /var/lib/nuxel/permissions/nuxel-settings.json.nuxel-rollback.pre-deploy-20261027T172231-2153662; fi
test -f /var/lib/nuxel/permissions/nuxel-settings.json.nuxel-staged
printf '%s  %s\n' dce7f242c18b5a56328b53d9c4a681141a3075298bd13030d463b5cfcadb77b8 /var/lib/nuxel/permissions/nuxel-settings.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /var/lib/nuxel/permissions/nuxel-settings.json.nuxel-staged /var/lib/nuxel/permissions/nuxel-settings.json
sha256sum /var/lib/nuxel/permissions/nuxel-settings.json | grep -q dce7f242c18b5a56328b53d9c4a681141a3075298bd13030d463b5cfcadb77b8
echo INSTALL-OK
