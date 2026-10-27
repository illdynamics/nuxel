#!/bin/sh
# first-party capability grants and hardware config documents -> /var/lib/nuxel/permissions/org.nuxel.Home.json (service: nuxel-bridge, risk: medium)
# staged source: configs/nuxel/permissions/org.nuxel.Home.json
# previous-hash: e777f5bd7f341131cdad7c0936b1972753ed92e21faf741040af77308890407c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /var/lib/nuxel/permissions/org.nuxel.Home.json.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /var/lib/nuxel/permissions/org.nuxel.Home.json.nuxel-rollback.pre-v070-delta-release3 /var/lib/nuxel/permissions/org.nuxel.Home.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -d /var/lib/nuxel/permissions
if [ -e /var/lib/nuxel/permissions/org.nuxel.Home.json ]; then printf 'PREV=%s\n' "$(sha256sum /var/lib/nuxel/permissions/org.nuxel.Home.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /var/lib/nuxel/permissions/org.nuxel.Home.json)"
if [ -e /var/lib/nuxel/permissions/org.nuxel.Home.json ] && [ ! -e /var/lib/nuxel/permissions/org.nuxel.Home.json.nuxel-rollback ]; then cp -a /var/lib/nuxel/permissions/org.nuxel.Home.json /var/lib/nuxel/permissions/org.nuxel.Home.json.nuxel-rollback; fi
if [ -e /var/lib/nuxel/permissions/org.nuxel.Home.json ] && [ ! -e /var/lib/nuxel/permissions/org.nuxel.Home.json.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /var/lib/nuxel/permissions/org.nuxel.Home.json /var/lib/nuxel/permissions/org.nuxel.Home.json.nuxel-rollback.pre-v070-delta-release3; fi
test -f /var/lib/nuxel/permissions/org.nuxel.Home.json.nuxel-staged
printf '%s  %s\n' e777f5bd7f341131cdad7c0936b1972753ed92e21faf741040af77308890407c /var/lib/nuxel/permissions/org.nuxel.Home.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /var/lib/nuxel/permissions/org.nuxel.Home.json.nuxel-staged /var/lib/nuxel/permissions/org.nuxel.Home.json
sha256sum /var/lib/nuxel/permissions/org.nuxel.Home.json | grep -q e777f5bd7f341131cdad7c0936b1972753ed92e21faf741040af77308890407c
echo INSTALL-OK
