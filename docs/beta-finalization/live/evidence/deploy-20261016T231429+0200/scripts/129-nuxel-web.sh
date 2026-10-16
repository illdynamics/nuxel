#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/bin/nuxel-web (service: None, risk: medium)
# staged source: services/nuxel-web/bin/nuxel-web
# previous-hash: 636d5972d5b8786c2fceed952dc74e75c6d36fd98efe8a32c6c2863362ea7a32
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/bin/nuxel-web.nuxel-rollback ]; then cp -a /usr/bin/nuxel-web.nuxel-rollback /usr/bin/nuxel-web; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/bin/nuxel-web ]; then printf 'PREV=%s\n' "$(sha256sum /usr/bin/nuxel-web | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/bin/nuxel-web)"
if [ -e /usr/bin/nuxel-web ] && [ ! -e /usr/bin/nuxel-web.nuxel-rollback ]; then cp -a /usr/bin/nuxel-web /usr/bin/nuxel-web.nuxel-rollback; fi
test -f /usr/bin/nuxel-web.nuxel-staged
printf '%s  %s\n' 636d5972d5b8786c2fceed952dc74e75c6d36fd98efe8a32c6c2863362ea7a32 /usr/bin/nuxel-web.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/bin/nuxel-web.nuxel-staged /usr/bin/nuxel-web
sha256sum /usr/bin/nuxel-web | grep -q 636d5972d5b8786c2fceed952dc74e75c6d36fd98efe8a32c6c2863362ea7a32
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
systemctl daemon-reload
echo INSTALL-OK
