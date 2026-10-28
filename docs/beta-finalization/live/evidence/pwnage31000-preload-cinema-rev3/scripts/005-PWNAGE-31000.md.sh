#!/bin/sh
# Bounded pre-lockscreen video controller, systemd unit, durable config and supplied clip -> /usr/share/nuxel/doc/PWNAGE-31000.md (service: None, risk: low)
# staged source: docs/pwnage-31000/IMPLEMENTATION.md
# previous-hash: fbc60cbcf7543ef5fd5971975b11faddb8033aa123954bc50f6914b4b77b76bd
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback.pre-deploy-20261028T105710-2836090 ]; then cp -a /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback.pre-deploy-20261028T105710-2836090 /usr/share/nuxel/doc/PWNAGE-31000.md; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/doc/PWNAGE-31000.md ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/doc/PWNAGE-31000.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/doc/PWNAGE-31000.md)"
if [ -e /usr/share/nuxel/doc/PWNAGE-31000.md ] && [ ! -e /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback ]; then cp -a /usr/share/nuxel/doc/PWNAGE-31000.md /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback; fi
if [ -e /usr/share/nuxel/doc/PWNAGE-31000.md ] && [ ! -e /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback.pre-deploy-20261028T105710-2836090 ]; then cp -a /usr/share/nuxel/doc/PWNAGE-31000.md /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback.pre-deploy-20261028T105710-2836090; fi
test -f /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-staged
printf '%s  %s\n' fbc60cbcf7543ef5fd5971975b11faddb8033aa123954bc50f6914b4b77b76bd /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-staged /usr/share/nuxel/doc/PWNAGE-31000.md
sha256sum /usr/share/nuxel/doc/PWNAGE-31000.md | grep -q fbc60cbcf7543ef5fd5971975b11faddb8033aa123954bc50f6914b4b77b76bd
echo INSTALL-OK
