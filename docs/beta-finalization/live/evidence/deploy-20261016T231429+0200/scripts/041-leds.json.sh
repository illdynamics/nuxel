#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/leds/leds.json (service: None, risk: medium)
# staged source: configs/nuxel/leds/leds.json
# previous-hash: d4a9d482d79366210df0b07f12cfa8ce0e5c472f3a777f6aa616517d2ca8cb49
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/leds/leds.json.nuxel-rollback ]; then cp -a /etc/nuxel/leds/leds.json.nuxel-rollback /etc/nuxel/leds/leds.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/leds/leds.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/leds/leds.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/leds/leds.json)"
if [ -e /etc/nuxel/leds/leds.json ] && [ ! -e /etc/nuxel/leds/leds.json.nuxel-rollback ]; then cp -a /etc/nuxel/leds/leds.json /etc/nuxel/leds/leds.json.nuxel-rollback; fi
test -f /etc/nuxel/leds/leds.json.nuxel-staged
printf '%s  %s\n' d4a9d482d79366210df0b07f12cfa8ce0e5c472f3a777f6aa616517d2ca8cb49 /etc/nuxel/leds/leds.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/leds/leds.json.nuxel-staged /etc/nuxel/leds/leds.json
sha256sum /etc/nuxel/leds/leds.json | grep -q d4a9d482d79366210df0b07f12cfa8ce0e5c472f3a777f6aa616517d2ca8cb49
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
