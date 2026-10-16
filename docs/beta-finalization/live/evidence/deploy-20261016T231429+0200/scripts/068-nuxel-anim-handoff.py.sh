#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/libexec/nuxel/nuxel-anim-handoff.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-anim-handoff.py
# previous-hash: 1d656083f21b37c76ae3eccca870265d15aa46151b90bc61daf68a3e37d61c67
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/libexec/nuxel/nuxel-anim-handoff.py.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-anim-handoff.py.nuxel-rollback /usr/libexec/nuxel/nuxel-anim-handoff.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/libexec/nuxel/nuxel-anim-handoff.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/libexec/nuxel/nuxel-anim-handoff.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/libexec/nuxel/nuxel-anim-handoff.py)"
if [ -e /usr/libexec/nuxel/nuxel-anim-handoff.py ] && [ ! -e /usr/libexec/nuxel/nuxel-anim-handoff.py.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-anim-handoff.py /usr/libexec/nuxel/nuxel-anim-handoff.py.nuxel-rollback; fi
test -f /usr/libexec/nuxel/nuxel-anim-handoff.py.nuxel-staged
printf '%s  %s\n' 1d656083f21b37c76ae3eccca870265d15aa46151b90bc61daf68a3e37d61c67 /usr/libexec/nuxel/nuxel-anim-handoff.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/libexec/nuxel/nuxel-anim-handoff.py.nuxel-staged /usr/libexec/nuxel/nuxel-anim-handoff.py
sha256sum /usr/libexec/nuxel/nuxel-anim-handoff.py | grep -q 1d656083f21b37c76ae3eccca870265d15aa46151b90bc61daf68a3e37d61c67
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
