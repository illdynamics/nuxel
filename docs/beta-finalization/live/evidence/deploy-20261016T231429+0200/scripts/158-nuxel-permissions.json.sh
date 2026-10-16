#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-permissions.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-permissions.json
# previous-hash: 9ff3870314de94d83859d02a7521354c1268b4b3d90ebe3143ee400be4fa8b62
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-permissions.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sandbox/profiles/nuxel-permissions.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sandbox/profiles/nuxel-permissions.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-permissions.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-permissions.json ] && [ ! -e /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-permissions.json /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-staged
printf '%s  %s\n' 9ff3870314de94d83859d02a7521354c1268b4b3d90ebe3143ee400be4fa8b62 /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-permissions.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-permissions.json | grep -q 9ff3870314de94d83859d02a7521354c1268b4b3d90ebe3143ee400be4fa8b62
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
