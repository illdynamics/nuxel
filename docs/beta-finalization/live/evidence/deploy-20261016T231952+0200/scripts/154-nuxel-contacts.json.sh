#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-contacts.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-contacts.json
# previous-hash: 0d00542af13713070cd5e8027c1b54a09343ef7d19f28e1fb4795ee43c6410d4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sandbox/profiles/nuxel-contacts.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-contacts.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-contacts.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sandbox/profiles/nuxel-contacts.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sandbox/profiles/nuxel-contacts.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-contacts.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-contacts.json ] && [ ! -e /etc/nuxel/sandbox/profiles/nuxel-contacts.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-contacts.json /etc/nuxel/sandbox/profiles/nuxel-contacts.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-contacts.json.nuxel-staged
printf '%s  %s\n' 0d00542af13713070cd5e8027c1b54a09343ef7d19f28e1fb4795ee43c6410d4 /etc/nuxel/sandbox/profiles/nuxel-contacts.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-contacts.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-contacts.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-contacts.json | grep -q 0d00542af13713070cd5e8027c1b54a09343ef7d19f28e1fb4795ee43c6410d4
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
