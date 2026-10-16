#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-dialer.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-dialer.json
# previous-hash: c118f58a9636081896a79fb8a9aa9a026fedbdc3a25ff4b51ae4518bd9f13ea8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-dialer.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/sandbox/profiles/nuxel-dialer.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/sandbox/profiles/nuxel-dialer.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-dialer.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-dialer.json ] && [ ! -e /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-dialer.json /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-staged
printf '%s  %s\n' c118f58a9636081896a79fb8a9aa9a026fedbdc3a25ff4b51ae4518bd9f13ea8 /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-dialer.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-dialer.json | grep -q c118f58a9636081896a79fb8a9aa9a026fedbdc3a25ff4b51ae4518bd9f13ea8
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
