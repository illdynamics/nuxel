#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/security/tor/torrc (service: None, risk: medium)
# staged source: configs/nuxel/security/tor/torrc
# previous-hash: f9185c6ce163080b291a6969a179ff565bef501ca862198bbb53f9d411e94053
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/security/tor/torrc.nuxel-rollback ]; then cp -a /etc/nuxel/security/tor/torrc.nuxel-rollback /etc/nuxel/security/tor/torrc; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/security/tor/torrc ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/security/tor/torrc | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/security/tor/torrc)"
if [ -e /etc/nuxel/security/tor/torrc ] && [ ! -e /etc/nuxel/security/tor/torrc.nuxel-rollback ]; then cp -a /etc/nuxel/security/tor/torrc /etc/nuxel/security/tor/torrc.nuxel-rollback; fi
test -f /etc/nuxel/security/tor/torrc.nuxel-staged
printf '%s  %s\n' f9185c6ce163080b291a6969a179ff565bef501ca862198bbb53f9d411e94053 /etc/nuxel/security/tor/torrc.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/security/tor/torrc.nuxel-staged /etc/nuxel/security/tor/torrc
sha256sum /etc/nuxel/security/tor/torrc | grep -q f9185c6ce163080b291a6969a179ff565bef501ca862198bbb53f9d411e94053
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
