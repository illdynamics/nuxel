#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/_shared/samples/sys-snapshot.json
# previous-hash: 31d707cd898d2fb561478994498446806f75bb431c947a1d117d08e6cfe2ff19
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-staged
printf '%s  %s\n' 31d707cd898d2fb561478994498446806f75bb431c947a1d117d08e6cfe2ff19 /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json | grep -q 31d707cd898d2fb561478994498446806f75bb431c947a1d117d08e6cfe2ff19
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
