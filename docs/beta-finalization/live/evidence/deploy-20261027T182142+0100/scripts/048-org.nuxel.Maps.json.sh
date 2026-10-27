#!/bin/sh
# first-party capability grants and hardware config documents -> /var/lib/nuxel/permissions/org.nuxel.Maps.json (service: nuxel-bridge, risk: medium)
# staged source: configs/nuxel/permissions/org.nuxel.Maps.json
# previous-hash: 5ae4dd9ddc54b128cf5cb036d63dbac2b22c42c713767ad86dee3817ea6ef587
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /var/lib/nuxel/permissions/org.nuxel.Maps.json.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /var/lib/nuxel/permissions/org.nuxel.Maps.json.nuxel-rollback.pre-deploy-20261027T182142-2202036 /var/lib/nuxel/permissions/org.nuxel.Maps.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -d /var/lib/nuxel/permissions
if [ -e /var/lib/nuxel/permissions/org.nuxel.Maps.json ]; then printf 'PREV=%s\n' "$(sha256sum /var/lib/nuxel/permissions/org.nuxel.Maps.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /var/lib/nuxel/permissions/org.nuxel.Maps.json)"
if [ -e /var/lib/nuxel/permissions/org.nuxel.Maps.json ] && [ ! -e /var/lib/nuxel/permissions/org.nuxel.Maps.json.nuxel-rollback ]; then cp -a /var/lib/nuxel/permissions/org.nuxel.Maps.json /var/lib/nuxel/permissions/org.nuxel.Maps.json.nuxel-rollback; fi
if [ -e /var/lib/nuxel/permissions/org.nuxel.Maps.json ] && [ ! -e /var/lib/nuxel/permissions/org.nuxel.Maps.json.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /var/lib/nuxel/permissions/org.nuxel.Maps.json /var/lib/nuxel/permissions/org.nuxel.Maps.json.nuxel-rollback.pre-deploy-20261027T182142-2202036; fi
test -f /var/lib/nuxel/permissions/org.nuxel.Maps.json.nuxel-staged
printf '%s  %s\n' 5ae4dd9ddc54b128cf5cb036d63dbac2b22c42c713767ad86dee3817ea6ef587 /var/lib/nuxel/permissions/org.nuxel.Maps.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /var/lib/nuxel/permissions/org.nuxel.Maps.json.nuxel-staged /var/lib/nuxel/permissions/org.nuxel.Maps.json
sha256sum /var/lib/nuxel/permissions/org.nuxel.Maps.json | grep -q 5ae4dd9ddc54b128cf5cb036d63dbac2b22c42c713767ad86dee3817ea6ef587
echo INSTALL-OK
