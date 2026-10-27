#!/bin/sh
# v0.7.1-beta PWA version pins and launcher cache namespace -> /usr/share/nuxel/pwa/nuxel-common/package.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/package.json
# previous-hash: d829f4330dbf076f6135e127d99586ae7ca46e4e5138302ff18010d5818621e1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/package.json.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/package.json.nuxel-rollback.pre-deploy-20261027T214523-2399095 /usr/share/nuxel/pwa/nuxel-common/package.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/package.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/package.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/package.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/package.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/package.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/package.json /usr/share/nuxel/pwa/nuxel-common/package.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/package.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/package.json.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/package.json /usr/share/nuxel/pwa/nuxel-common/package.json.nuxel-rollback.pre-deploy-20261027T214523-2399095; fi
test -f /usr/share/nuxel/pwa/nuxel-common/package.json.nuxel-staged
printf '%s  %s\n' d829f4330dbf076f6135e127d99586ae7ca46e4e5138302ff18010d5818621e1 /usr/share/nuxel/pwa/nuxel-common/package.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/package.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/package.json
sha256sum /usr/share/nuxel/pwa/nuxel-common/package.json | grep -q d829f4330dbf076f6135e127d99586ae7ca46e4e5138302ff18010d5818621e1
echo INSTALL-OK
