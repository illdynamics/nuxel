#!/bin/sh
# audio / network runtime config -> /etc/nuxel/audio/jack-routes.json (service: nuxel-audio, risk: medium)
# staged source: configs/nuxel/audio/jack-routes.json
# previous-hash: 4f6117835fb8787d93f5a2e2b0def9962b7056c00b9bc78ffc9ec5ac4fae9309
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/audio/jack-routes.json.nuxel-rollback ]; then cp -a /etc/nuxel/audio/jack-routes.json.nuxel-rollback /etc/nuxel/audio/jack-routes.json; systemctl restart nuxel-audio; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/audio/jack-routes.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/audio/jack-routes.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/audio/jack-routes.json)"
if [ -e /etc/nuxel/audio/jack-routes.json ] && [ ! -e /etc/nuxel/audio/jack-routes.json.nuxel-rollback ]; then cp -a /etc/nuxel/audio/jack-routes.json /etc/nuxel/audio/jack-routes.json.nuxel-rollback; fi
test -f /etc/nuxel/audio/jack-routes.json.nuxel-staged
printf '%s  %s\n' 4f6117835fb8787d93f5a2e2b0def9962b7056c00b9bc78ffc9ec5ac4fae9309 /etc/nuxel/audio/jack-routes.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/audio/jack-routes.json.nuxel-staged /etc/nuxel/audio/jack-routes.json
sha256sum /etc/nuxel/audio/jack-routes.json | grep -q 4f6117835fb8787d93f5a2e2b0def9962b7056c00b9bc78ffc9ec5ac4fae9309
systemctl restart nuxel-audio
systemctl is-active nuxel-audio
echo INSTALL-OK
