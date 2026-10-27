#!/bin/sh
# first-party capability grants and hardware config documents -> /etc/nuxel/security/remote-access.json (service: nuxel-bridge, risk: medium)
# staged source: configs/nuxel/security/remote-access.json
# previous-hash: 9c107eddcd780874f0e018d3f75198e2af162a259a5e229d9584815f989f8d67
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/security/remote-access.json.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /etc/nuxel/security/remote-access.json.nuxel-rollback.pre-deploy-20261027T180728-2189607 /etc/nuxel/security/remote-access.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -d /var/lib/nuxel/permissions
if [ -e /etc/nuxel/security/remote-access.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/security/remote-access.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/security/remote-access.json)"
if [ -e /etc/nuxel/security/remote-access.json ] && [ ! -e /etc/nuxel/security/remote-access.json.nuxel-rollback ]; then cp -a /etc/nuxel/security/remote-access.json /etc/nuxel/security/remote-access.json.nuxel-rollback; fi
if [ -e /etc/nuxel/security/remote-access.json ] && [ ! -e /etc/nuxel/security/remote-access.json.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /etc/nuxel/security/remote-access.json /etc/nuxel/security/remote-access.json.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /etc/nuxel/security/remote-access.json.nuxel-staged
printf '%s  %s\n' 9c107eddcd780874f0e018d3f75198e2af162a259a5e229d9584815f989f8d67 /etc/nuxel/security/remote-access.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/security/remote-access.json.nuxel-staged /etc/nuxel/security/remote-access.json
sha256sum /etc/nuxel/security/remote-access.json | grep -q 9c107eddcd780874f0e018d3f75198e2af162a259a5e229d9584815f989f8d67
echo INSTALL-OK
