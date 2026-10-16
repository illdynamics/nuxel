#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-settings.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-settings.json
# previous-hash: 1bfbb71af58b0ea63f0651b911e582b120a8ebdea534a83b5352170e4ce230ed
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-settings.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sandbox/profiles/nuxel-settings.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sandbox/profiles/nuxel-settings.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-settings.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-settings.json ] && [ ! -e /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-settings.json /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-staged
printf '%s  %s\n' 1bfbb71af58b0ea63f0651b911e582b120a8ebdea534a83b5352170e4ce230ed /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-settings.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-settings.json | grep -q 1bfbb71af58b0ea63f0651b911e582b120a8ebdea534a83b5352170e4ce230ed
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
