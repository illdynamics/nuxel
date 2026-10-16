#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-console-free (service: None, risk: medium)
# staged source: services/nuxel-console/bin/nuxel-console-free
# previous-hash: bb46c39dcd8f35ca64189b2cbbd42aa7f3ef516347868bb01651ca61a02ba0b3
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-console-free)"
if [ -e /usr/lib/nuxel/nuxel-console-free ]; then cp -a /usr/lib/nuxel/nuxel-console-free /usr/lib/nuxel/nuxel-console-free.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-console-free.nuxel-staged
printf '%s  %s\n' bb46c39dcd8f35ca64189b2cbbd42aa7f3ef516347868bb01651ca61a02ba0b3 /usr/lib/nuxel/nuxel-console-free.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-console-free.nuxel-staged /usr/lib/nuxel/nuxel-console-free
sha256sum /usr/lib/nuxel/nuxel-console-free | grep -q bb46c39dcd8f35ca64189b2cbbd42aa7f3ef516347868bb01651ca61a02ba0b3
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-console-free.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-console-free.nuxel-rollback /usr/lib/nuxel/nuxel-console-free; true; fi
