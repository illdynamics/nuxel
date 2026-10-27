#!/bin/sh
# PWNAGE-30000 bridge persistence and mail transport -> /usr/lib/nuxel/nuxel-bridge/mail_client.py (service: nuxel-http-bridge.service, risk: medium)
# staged source: services/nuxel-bridge/src/mail_client.py
# previous-hash: 00f5f5b84ecea42d950d5d7379fd17af3df3a9d58d191d97c24f6aabc0c2404d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/mail_client.py.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/mail_client.py.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/lib/nuxel/nuxel-bridge/mail_client.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/mail_client.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/mail_client.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/mail_client.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/mail_client.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/mail_client.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/mail_client.py /usr/lib/nuxel/nuxel-bridge/mail_client.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/mail_client.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/mail_client.py.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/mail_client.py /usr/lib/nuxel/nuxel-bridge/mail_client.py.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/lib/nuxel/nuxel-bridge/mail_client.py.nuxel-staged
printf '%s  %s\n' 00f5f5b84ecea42d950d5d7379fd17af3df3a9d58d191d97c24f6aabc0c2404d /usr/lib/nuxel/nuxel-bridge/mail_client.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/mail_client.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/mail_client.py
sha256sum /usr/lib/nuxel/nuxel-bridge/mail_client.py | grep -q 00f5f5b84ecea42d950d5d7379fd17af3df3a9d58d191d97c24f6aabc0c2404d
echo INSTALL-OK
