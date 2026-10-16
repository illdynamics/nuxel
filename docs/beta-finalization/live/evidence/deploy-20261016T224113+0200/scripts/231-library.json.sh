#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/samples/library.json
# previous-hash: fe949d78fb8c583f222c65c90bda7bc772778a012abeb47af47c45c871b786fc
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json.nuxel-staged
printf '%s  %s\n' fe949d78fb8c583f222c65c90bda7bc772778a012abeb47af47c45c871b786fc /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/samples/library.json | grep -q fe949d78fb8c583f222c65c90bda7bc772778a012abeb47af47c45c871b786fc
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
