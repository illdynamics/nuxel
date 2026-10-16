#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/downloader/samples/queue-examples.json
# previous-hash: c6a4cb3820bef5edc7d037c4a403074a1499f1db255c905c7876c89f629a4d60
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json.nuxel-staged
printf '%s  %s\n' c6a4cb3820bef5edc7d037c4a403074a1499f1db255c905c7876c89f629a4d60 /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/samples/queue-examples.json | grep -q c6a4cb3820bef5edc7d037c4a403074a1499f1db255c905c7876c89f629a4d60
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
