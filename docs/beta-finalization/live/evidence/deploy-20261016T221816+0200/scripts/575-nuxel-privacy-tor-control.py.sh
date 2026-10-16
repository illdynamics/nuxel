#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/local/bin/nuxel-privacy-tor-control.py (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-privacy/tor-control.py
# previous-hash: a1ba949e7474a38034e08bfbf686c53d87737aabe9f6fa809678dbb2dd413234
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-privacy-tor-control.py)"
if [ -e /usr/local/bin/nuxel-privacy-tor-control.py ]; then cp -a /usr/local/bin/nuxel-privacy-tor-control.py /usr/local/bin/nuxel-privacy-tor-control.py.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-privacy-tor-control.py.nuxel-staged
printf '%s  %s\n' a1ba949e7474a38034e08bfbf686c53d87737aabe9f6fa809678dbb2dd413234 /usr/local/bin/nuxel-privacy-tor-control.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-privacy-tor-control.py.nuxel-staged /usr/local/bin/nuxel-privacy-tor-control.py
sha256sum /usr/local/bin/nuxel-privacy-tor-control.py | grep -q a1ba949e7474a38034e08bfbf686c53d87737aabe9f6fa809678dbb2dd413234
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-privacy-tor-control.py.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-privacy-tor-control.py.nuxel-rollback /usr/local/bin/nuxel-privacy-tor-control.py; true; fi
