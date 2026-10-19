#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-osm-tiles.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-osm-tiles.py
# previous-hash: abd09f763519a816e25f699ff2afe59ec4a61d1fa582321637b1921d2979dfbb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-osm-tiles.py.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-osm-tiles.py.nuxel-rollback /usr/local/bin/nuxel-osm-tiles.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-osm-tiles.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-osm-tiles.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-osm-tiles.py)"
if [ -e /usr/local/bin/nuxel-osm-tiles.py ] && [ ! -e /usr/local/bin/nuxel-osm-tiles.py.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-osm-tiles.py /usr/local/bin/nuxel-osm-tiles.py.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-osm-tiles.py.nuxel-staged
printf '%s  %s\n' abd09f763519a816e25f699ff2afe59ec4a61d1fa582321637b1921d2979dfbb /usr/local/bin/nuxel-osm-tiles.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-osm-tiles.py.nuxel-staged /usr/local/bin/nuxel-osm-tiles.py
sha256sum /usr/local/bin/nuxel-osm-tiles.py | grep -q abd09f763519a816e25f699ff2afe59ec4a61d1fa582321637b1921d2979dfbb
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
