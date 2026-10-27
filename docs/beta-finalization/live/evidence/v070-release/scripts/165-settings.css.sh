#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/settings.css
# previous-hash: 13292e21cdcfdf379aa6489bdc87cad4a857e92d6f163242d177ce1d54056c71
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-staged
printf '%s  %s\n' 13292e21cdcfdf379aa6489bdc87cad4a857e92d6f163242d177ce1d54056c71 /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css | grep -q 13292e21cdcfdf379aa6489bdc87cad4a857e92d6f163242d177ce1d54056c71
echo INSTALL-OK
