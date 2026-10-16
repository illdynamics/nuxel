#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/recorder/css/recorder.css
# previous-hash: 7ed3e7dcdc84edbc22a63cdb1520c956dbb83d43830533fa86ac8958a0028672
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-staged
printf '%s  %s\n' 7ed3e7dcdc84edbc22a63cdb1520c956dbb83d43830533fa86ac8958a0028672 /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css | grep -q 7ed3e7dcdc84edbc22a63cdb1520c956dbb83d43830533fa86ac8958a0028672
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
