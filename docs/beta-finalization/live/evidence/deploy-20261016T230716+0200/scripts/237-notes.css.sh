#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/css/notes.css
# previous-hash: 9be51e4fd8e7570c7235b67ec22c0c479cdb0f980ca086a2552cfd1d6558098b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-staged
printf '%s  %s\n' 9be51e4fd8e7570c7235b67ec22c0c479cdb0f980ca086a2552cfd1d6558098b /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css | grep -q 9be51e4fd8e7570c7235b67ec22c0c479cdb0f980ca086a2552cfd1d6558098b
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
