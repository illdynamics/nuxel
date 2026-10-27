#!/bin/sh
# v0.7.1-beta PWA version pins and launcher cache namespace -> /usr/share/nuxel/VERSION (service: nuxel-web, risk: low)
# staged source: VERSION
# previous-hash: b287d08216e6d93bf363f67d448919c67711c1fb80aa148d45be77cf585a8be2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/VERSION.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/share/nuxel/VERSION.nuxel-rollback.pre-deploy-20261027T214530-2399261 /usr/share/nuxel/VERSION; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/VERSION ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/VERSION | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/VERSION)"
if [ -e /usr/share/nuxel/VERSION ] && [ ! -e /usr/share/nuxel/VERSION.nuxel-rollback ]; then cp -a /usr/share/nuxel/VERSION /usr/share/nuxel/VERSION.nuxel-rollback; fi
if [ -e /usr/share/nuxel/VERSION ] && [ ! -e /usr/share/nuxel/VERSION.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/share/nuxel/VERSION /usr/share/nuxel/VERSION.nuxel-rollback.pre-deploy-20261027T214530-2399261; fi
test -f /usr/share/nuxel/VERSION.nuxel-staged
printf '%s  %s\n' b287d08216e6d93bf363f67d448919c67711c1fb80aa148d45be77cf585a8be2 /usr/share/nuxel/VERSION.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/VERSION.nuxel-staged /usr/share/nuxel/VERSION
sha256sum /usr/share/nuxel/VERSION | grep -q b287d08216e6d93bf363f67d448919c67711c1fb80aa148d45be77cf585a8be2
echo INSTALL-OK
