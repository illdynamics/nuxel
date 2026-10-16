#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/manifest.json
# previous-hash: 1db557dea085a8979667a100d969ed393ae18c8ed3659466c18393f518bee565
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json.nuxel-staged
printf '%s  %s\n' 1db557dea085a8979667a100d969ed393ae18c8ed3659466c18393f518bee565 /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/manifest.json | grep -q 1db557dea085a8979667a100d969ed393ae18c8ed3659466c18393f518bee565
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
