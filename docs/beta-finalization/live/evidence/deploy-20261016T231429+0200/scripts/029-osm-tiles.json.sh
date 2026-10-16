#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/gnss/osm-tiles.json (service: None, risk: medium)
# staged source: configs/nuxel/gnss/osm-tiles.json
# previous-hash: 879346a344b589c49a1222f884de4958400e584b937fb53f639d8aa8dfee0516
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/gnss/osm-tiles.json.nuxel-rollback ]; then cp -a /etc/nuxel/gnss/osm-tiles.json.nuxel-rollback /etc/nuxel/gnss/osm-tiles.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/gnss/osm-tiles.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/gnss/osm-tiles.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/gnss/osm-tiles.json)"
if [ -e /etc/nuxel/gnss/osm-tiles.json ] && [ ! -e /etc/nuxel/gnss/osm-tiles.json.nuxel-rollback ]; then cp -a /etc/nuxel/gnss/osm-tiles.json /etc/nuxel/gnss/osm-tiles.json.nuxel-rollback; fi
test -f /etc/nuxel/gnss/osm-tiles.json.nuxel-staged
printf '%s  %s\n' 879346a344b589c49a1222f884de4958400e584b937fb53f639d8aa8dfee0516 /etc/nuxel/gnss/osm-tiles.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/gnss/osm-tiles.json.nuxel-staged /etc/nuxel/gnss/osm-tiles.json
sha256sum /etc/nuxel/gnss/osm-tiles.json | grep -q 879346a344b589c49a1222f884de4958400e584b937fb53f639d8aa8dfee0516
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
