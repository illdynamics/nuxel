#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/terminal/terminal.css
# previous-hash: be6132b04a605c6dc0546f8a153da94d0675836b9650c04bcaca5093a2dda41b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-staged
printf '%s  %s\n' be6132b04a605c6dc0546f8a153da94d0675836b9650c04bcaca5093a2dda41b /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css | grep -q be6132b04a605c6dc0546f8a153da94d0675836b9650c04bcaca5093a2dda41b
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
