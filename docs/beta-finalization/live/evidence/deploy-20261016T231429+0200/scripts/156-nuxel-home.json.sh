#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-home.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-home.json
# previous-hash: 4da28388b2062e13f1db6823350b55064654cc579bfd409b7ef3049a57dfa019
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-home.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sandbox/profiles/nuxel-home.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sandbox/profiles/nuxel-home.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-home.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-home.json ] && [ ! -e /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-home.json /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-staged
printf '%s  %s\n' 4da28388b2062e13f1db6823350b55064654cc579bfd409b7ef3049a57dfa019 /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-home.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-home.json | grep -q 4da28388b2062e13f1db6823350b55064654cc579bfd409b7ef3049a57dfa019
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
