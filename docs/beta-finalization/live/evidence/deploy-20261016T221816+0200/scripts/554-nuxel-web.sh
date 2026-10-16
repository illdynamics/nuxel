#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/bin/nuxel-web (service: None, risk: medium)
# staged source: services/nuxel-web/bin/nuxel-web
# previous-hash: 636d5972d5b8786c2fceed952dc74e75c6d36fd98efe8a32c6c2863362ea7a32
set -eu
mkdir -p "$(dirname /usr/bin/nuxel-web)"
if [ -e /usr/bin/nuxel-web ]; then cp -a /usr/bin/nuxel-web /usr/bin/nuxel-web.nuxel-rollback; fi
test -f /usr/bin/nuxel-web.nuxel-staged
printf '%s  %s\n' 636d5972d5b8786c2fceed952dc74e75c6d36fd98efe8a32c6c2863362ea7a32 /usr/bin/nuxel-web.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/bin/nuxel-web.nuxel-staged /usr/bin/nuxel-web
sha256sum /usr/bin/nuxel-web | grep -q 636d5972d5b8786c2fceed952dc74e75c6d36fd98efe8a32c6c2863362ea7a32
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/bin/nuxel-web.nuxel-rollback ]; then cp -a /usr/bin/nuxel-web.nuxel-rollback /usr/bin/nuxel-web; true; fi
