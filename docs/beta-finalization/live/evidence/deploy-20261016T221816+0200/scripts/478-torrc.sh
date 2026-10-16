#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/security/tor/torrc (service: None, risk: medium)
# staged source: configs/nuxel/security/tor/torrc
# previous-hash: f9185c6ce163080b291a6969a179ff565bef501ca862198bbb53f9d411e94053
set -eu
mkdir -p "$(dirname /etc/nuxel/security/tor/torrc)"
if [ -e /etc/nuxel/security/tor/torrc ]; then cp -a /etc/nuxel/security/tor/torrc /etc/nuxel/security/tor/torrc.nuxel-rollback; fi
test -f /etc/nuxel/security/tor/torrc.nuxel-staged
printf '%s  %s\n' f9185c6ce163080b291a6969a179ff565bef501ca862198bbb53f9d411e94053 /etc/nuxel/security/tor/torrc.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/security/tor/torrc.nuxel-staged /etc/nuxel/security/tor/torrc
sha256sum /etc/nuxel/security/tor/torrc | grep -q f9185c6ce163080b291a6969a179ff565bef501ca862198bbb53f9d411e94053
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/security/tor/torrc.nuxel-rollback ]; then cp -a /etc/nuxel/security/tor/torrc.nuxel-rollback /etc/nuxel/security/tor/torrc; true; fi
