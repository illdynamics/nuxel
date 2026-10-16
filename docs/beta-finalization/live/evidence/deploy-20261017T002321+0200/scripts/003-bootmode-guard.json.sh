#!/bin/sh
# touch / hardware buttons -> /etc/nuxel/touch/bootmode-guard.json (service: nuxel-touch-arm, risk: medium)
# staged source: configs/nuxel/touch/bootmode-guard.json
# previous-hash: 705d8bacf98894a0f131318cb9342902b1c8cc90e278111c0e4fe68b2ffcd418
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/touch/bootmode-guard.json.nuxel-rollback ]; then cp -a /etc/nuxel/touch/bootmode-guard.json.nuxel-rollback /etc/nuxel/touch/bootmode-guard.json; systemctl restart nuxel-touch-arm; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/touch/bootmode-guard.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/touch/bootmode-guard.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/touch/bootmode-guard.json)"
if [ -e /etc/nuxel/touch/bootmode-guard.json ] && [ ! -e /etc/nuxel/touch/bootmode-guard.json.nuxel-rollback ]; then cp -a /etc/nuxel/touch/bootmode-guard.json /etc/nuxel/touch/bootmode-guard.json.nuxel-rollback; fi
test -f /etc/nuxel/touch/bootmode-guard.json.nuxel-staged
printf '%s  %s\n' 705d8bacf98894a0f131318cb9342902b1c8cc90e278111c0e4fe68b2ffcd418 /etc/nuxel/touch/bootmode-guard.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/touch/bootmode-guard.json.nuxel-staged /etc/nuxel/touch/bootmode-guard.json
sha256sum /etc/nuxel/touch/bootmode-guard.json | grep -q 705d8bacf98894a0f131318cb9342902b1c8cc90e278111c0e4fe68b2ffcd418
systemctl restart nuxel-touch-arm
systemctl is-active nuxel-touch-arm
echo INSTALL-OK
