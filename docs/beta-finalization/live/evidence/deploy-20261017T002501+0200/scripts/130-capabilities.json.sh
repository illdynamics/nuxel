#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/nuxel-permissions/capabilities.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-permissions/capabilities.json
# previous-hash: fea064b1d3bd05e1813d70447cd5f34d9bd900b8b599d665f85d27cef25a87e3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-rollback /usr/lib/nuxel/nuxel-permissions/capabilities.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-permissions/capabilities.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-permissions/capabilities.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-permissions/capabilities.json)"
if [ -e /usr/lib/nuxel/nuxel-permissions/capabilities.json ] && [ ! -e /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-permissions/capabilities.json /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-staged
printf '%s  %s\n' fea064b1d3bd05e1813d70447cd5f34d9bd900b8b599d665f85d27cef25a87e3 /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-staged /usr/lib/nuxel/nuxel-permissions/capabilities.json
sha256sum /usr/lib/nuxel/nuxel-permissions/capabilities.json | grep -q fea064b1d3bd05e1813d70447cd5f34d9bd900b8b599d665f85d27cef25a87e3
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
