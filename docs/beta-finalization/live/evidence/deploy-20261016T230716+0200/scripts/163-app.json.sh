#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/files/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/app.json
# previous-hash: 75041742b7a7cb192cf6d4b7a5cdcf104065ba4ac4e98e7e1be35de521b68e2c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/files/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/app.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/app.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/app.json /usr/share/nuxel/pwa/nuxel-apps/files/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/app.json.nuxel-staged
printf '%s  %s\n' 75041742b7a7cb192cf6d4b7a5cdcf104065ba4ac4e98e7e1be35de521b68e2c /usr/share/nuxel/pwa/nuxel-apps/files/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/app.json | grep -q 75041742b7a7cb192cf6d4b7a5cdcf104065ba4ac4e98e7e1be35de521b68e2c
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
