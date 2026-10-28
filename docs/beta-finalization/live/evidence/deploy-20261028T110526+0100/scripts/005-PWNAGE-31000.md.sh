#!/bin/sh
# Bounded pre-lockscreen video controller, systemd unit, durable config and supplied clip -> /usr/share/nuxel/doc/PWNAGE-31000.md (service: None, risk: low)
# staged source: docs/pwnage-31000/IMPLEMENTATION.md
# previous-hash: eaa1859f238142cacccacb38de63391427fdc47ccfe427cc449bf50055570079
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback.pre-deploy-20261028T110526-2846794 ]; then cp -a /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback.pre-deploy-20261028T110526-2846794 /usr/share/nuxel/doc/PWNAGE-31000.md; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/doc/PWNAGE-31000.md ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/doc/PWNAGE-31000.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/doc/PWNAGE-31000.md)"
if [ -e /usr/share/nuxel/doc/PWNAGE-31000.md ] && [ ! -e /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback ]; then cp -a /usr/share/nuxel/doc/PWNAGE-31000.md /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback; fi
if [ -e /usr/share/nuxel/doc/PWNAGE-31000.md ] && [ ! -e /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback.pre-deploy-20261028T110526-2846794 ]; then cp -a /usr/share/nuxel/doc/PWNAGE-31000.md /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback.pre-deploy-20261028T110526-2846794; fi
test -f /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-staged
printf '%s  %s\n' eaa1859f238142cacccacb38de63391427fdc47ccfe427cc449bf50055570079 /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-staged /usr/share/nuxel/doc/PWNAGE-31000.md
sha256sum /usr/share/nuxel/doc/PWNAGE-31000.md | grep -q eaa1859f238142cacccacb38de63391427fdc47ccfe427cc449bf50055570079
echo INSTALL-OK
