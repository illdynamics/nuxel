#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-console-free (service: None, risk: medium)
# staged source: services/nuxel-console/bin/nuxel-console-free
# previous-hash: bb46c39dcd8f35ca64189b2cbbd42aa7f3ef516347868bb01651ca61a02ba0b3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-console-free.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-console-free.nuxel-rollback /usr/lib/nuxel/nuxel-console-free; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-console-free ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-console-free | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-console-free)"
if [ -e /usr/lib/nuxel/nuxel-console-free ] && [ ! -e /usr/lib/nuxel/nuxel-console-free.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-console-free /usr/lib/nuxel/nuxel-console-free.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-console-free.nuxel-staged
printf '%s  %s\n' bb46c39dcd8f35ca64189b2cbbd42aa7f3ef516347868bb01651ca61a02ba0b3 /usr/lib/nuxel/nuxel-console-free.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-console-free.nuxel-staged /usr/lib/nuxel/nuxel-console-free
sha256sum /usr/lib/nuxel/nuxel-console-free | grep -q bb46c39dcd8f35ca64189b2cbbd42aa7f3ef516347868bb01651ca61a02ba0b3
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
systemctl daemon-reload
echo INSTALL-OK
