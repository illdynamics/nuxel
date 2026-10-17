#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/css/mail.css
# previous-hash: fd9e4f77cf8efbee2fdf663045e341ef0ea44329ef14454509a79aec86c7d17a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css.nuxel-staged
printf '%s  %s\n' fd9e4f77cf8efbee2fdf663045e341ef0ea44329ef14454509a79aec86c7d17a /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/css/mail.css | grep -q fd9e4f77cf8efbee2fdf663045e341ef0ea44329ef14454509a79aec86c7d17a
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
