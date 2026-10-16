#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-privacy.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-privacy.json
# previous-hash: 348302a4b284a39872eee81df904660eafb49fcd7476c9f9a8731f430e31a0b2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-privacy.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sandbox/profiles/nuxel-privacy.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sandbox/profiles/nuxel-privacy.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-privacy.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-privacy.json ] && [ ! -e /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-privacy.json /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-staged
printf '%s  %s\n' 348302a4b284a39872eee81df904660eafb49fcd7476c9f9a8731f430e31a0b2 /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-privacy.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-privacy.json | grep -q 348302a4b284a39872eee81df904660eafb49fcd7476c9f9a8731f430e31a0b2
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
