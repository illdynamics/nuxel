#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/input/button-fsm.json (service: None, risk: medium)
# staged source: configs/nuxel/input/button-fsm.json
# previous-hash: d1474ee35c89d796eb1a53c3a804efbfa4035db867ff3135ae65698becd9d8c6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/input/button-fsm.json.nuxel-rollback ]; then cp -a /etc/nuxel/input/button-fsm.json.nuxel-rollback /etc/nuxel/input/button-fsm.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/input/button-fsm.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/input/button-fsm.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/input/button-fsm.json)"
if [ -e /etc/nuxel/input/button-fsm.json ] && [ ! -e /etc/nuxel/input/button-fsm.json.nuxel-rollback ]; then cp -a /etc/nuxel/input/button-fsm.json /etc/nuxel/input/button-fsm.json.nuxel-rollback; fi
test -f /etc/nuxel/input/button-fsm.json.nuxel-staged
printf '%s  %s\n' d1474ee35c89d796eb1a53c3a804efbfa4035db867ff3135ae65698becd9d8c6 /etc/nuxel/input/button-fsm.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/input/button-fsm.json.nuxel-staged /etc/nuxel/input/button-fsm.json
sha256sum /etc/nuxel/input/button-fsm.json | grep -q d1474ee35c89d796eb1a53c3a804efbfa4035db867ff3135ae65698becd9d8c6
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
