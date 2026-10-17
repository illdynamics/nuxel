#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/keyboard/keyboard.json (service: None, risk: medium)
# staged source: configs/nuxel/keyboard/keyboard.json
# previous-hash: 9cef7e92b8ba4d64b2e6d8e70fc10706e9fc0d899930925f6e47032504fd55d2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/keyboard/keyboard.json.nuxel-rollback ]; then cp -a /etc/nuxel/keyboard/keyboard.json.nuxel-rollback /etc/nuxel/keyboard/keyboard.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/keyboard/keyboard.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/keyboard/keyboard.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/keyboard/keyboard.json)"
if [ -e /etc/nuxel/keyboard/keyboard.json ] && [ ! -e /etc/nuxel/keyboard/keyboard.json.nuxel-rollback ]; then cp -a /etc/nuxel/keyboard/keyboard.json /etc/nuxel/keyboard/keyboard.json.nuxel-rollback; fi
test -f /etc/nuxel/keyboard/keyboard.json.nuxel-staged
printf '%s  %s\n' 9cef7e92b8ba4d64b2e6d8e70fc10706e9fc0d899930925f6e47032504fd55d2 /etc/nuxel/keyboard/keyboard.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/keyboard/keyboard.json.nuxel-staged /etc/nuxel/keyboard/keyboard.json
sha256sum /etc/nuxel/keyboard/keyboard.json | grep -q 9cef7e92b8ba4d64b2e6d8e70fc10706e9fc0d899930925f6e47032504fd55d2
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
