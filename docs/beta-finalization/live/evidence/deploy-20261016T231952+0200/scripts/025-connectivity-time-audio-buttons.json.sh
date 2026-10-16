#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/capabilities/connectivity-time-audio-buttons.json (service: None, risk: medium)
# staged source: configs/nuxel/capabilities/connectivity-time-audio-buttons.json
# previous-hash: 5070421858a3ee61014390c365e31afaa2727ff96a89e4c82f32d55d82fb96e2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-rollback ]; then cp -a /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-rollback /etc/nuxel/capabilities/connectivity-time-audio-buttons.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/capabilities/connectivity-time-audio-buttons.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/capabilities/connectivity-time-audio-buttons.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/capabilities/connectivity-time-audio-buttons.json)"
if [ -e /etc/nuxel/capabilities/connectivity-time-audio-buttons.json ] && [ ! -e /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-rollback ]; then cp -a /etc/nuxel/capabilities/connectivity-time-audio-buttons.json /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-rollback; fi
test -f /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-staged
printf '%s  %s\n' 5070421858a3ee61014390c365e31afaa2727ff96a89e4c82f32d55d82fb96e2 /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-staged /etc/nuxel/capabilities/connectivity-time-audio-buttons.json
sha256sum /etc/nuxel/capabilities/connectivity-time-audio-buttons.json | grep -q 5070421858a3ee61014390c365e31afaa2727ff96a89e4c82f32d55d82fb96e2
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
