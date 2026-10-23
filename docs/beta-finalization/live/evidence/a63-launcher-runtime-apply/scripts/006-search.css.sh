#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/css/search.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/search.css
# previous-hash: 7854223714fe77cb7e69c62ca1ca9a1ffd02a41d7d3cc3014424f449ff4668f1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/css/search.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/search.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/search.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/search.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/search.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/search.css /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-staged
printf '%s  %s\n' 7854223714fe77cb7e69c62ca1ca9a1ffd02a41d7d3cc3014424f449ff4668f1 /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/search.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/search.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/search.css | grep -q 7854223714fe77cb7e69c62ca1ca9a1ffd02a41d7d3cc3014424f449ff4668f1
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
