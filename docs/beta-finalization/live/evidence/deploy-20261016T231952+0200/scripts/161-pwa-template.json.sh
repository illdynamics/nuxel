#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/pwa-template.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/pwa-template.json
# previous-hash: 841a21d486d45a0935dda2e196811cbdf4853814ec8de173c91aaab0503432db
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-rollback /etc/nuxel/sandbox/profiles/pwa-template.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sandbox/profiles/pwa-template.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sandbox/profiles/pwa-template.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/pwa-template.json)"
if [ -e /etc/nuxel/sandbox/profiles/pwa-template.json ] && [ ! -e /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/pwa-template.json /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-staged
printf '%s  %s\n' 841a21d486d45a0935dda2e196811cbdf4853814ec8de173c91aaab0503432db /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-staged /etc/nuxel/sandbox/profiles/pwa-template.json
sha256sum /etc/nuxel/sandbox/profiles/pwa-template.json | grep -q 841a21d486d45a0935dda2e196811cbdf4853814ec8de173c91aaab0503432db
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
