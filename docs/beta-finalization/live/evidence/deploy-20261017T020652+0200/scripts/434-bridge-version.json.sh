#!/bin/sh
# app registry consumers/entries + verifiers -> /etc/nuxel/bridge-version.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/bridge-version.json
# previous-hash: 510f0ce31556e175133295715cc822c93c88610e1c6188941b2580771864ad9a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/bridge-version.json.nuxel-rollback ]; then cp -a /etc/nuxel/bridge-version.json.nuxel-rollback /etc/nuxel/bridge-version.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/bridge-version.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/bridge-version.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/bridge-version.json)"
if [ -e /etc/nuxel/bridge-version.json ] && [ ! -e /etc/nuxel/bridge-version.json.nuxel-rollback ]; then cp -a /etc/nuxel/bridge-version.json /etc/nuxel/bridge-version.json.nuxel-rollback; fi
test -f /etc/nuxel/bridge-version.json.nuxel-staged
printf '%s  %s\n' 510f0ce31556e175133295715cc822c93c88610e1c6188941b2580771864ad9a /etc/nuxel/bridge-version.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bridge-version.json.nuxel-staged /etc/nuxel/bridge-version.json
sha256sum /etc/nuxel/bridge-version.json | grep -q 510f0ce31556e175133295715cc822c93c88610e1c6188941b2580771864ad9a
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
