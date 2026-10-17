#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-messages.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-messages.json
# previous-hash: 7ba696fb1f60138b0d83928e3fb8fd1eed3637529111b6ca4d491f05fa734ed4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-messages.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sandbox/profiles/nuxel-messages.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sandbox/profiles/nuxel-messages.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-messages.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-messages.json ] && [ ! -e /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-messages.json /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-staged
printf '%s  %s\n' 7ba696fb1f60138b0d83928e3fb8fd1eed3637529111b6ca4d491f05fa734ed4 /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-messages.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-messages.json | grep -q 7ba696fb1f60138b0d83928e3fb8fd1eed3637529111b6ca4d491f05fa734ed4
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
