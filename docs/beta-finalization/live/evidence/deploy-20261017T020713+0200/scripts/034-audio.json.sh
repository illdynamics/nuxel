#!/bin/sh
# audio / network runtime config -> /etc/nuxel/audio/audio.json (service: nuxel-audio, risk: medium)
# staged source: configs/nuxel/audio/audio.json
# previous-hash: 2630cd0afa96737f82fdab262de68f84fea01df6096e9100fbd3a2778b0e0185
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/audio/audio.json.nuxel-rollback ]; then cp -a /etc/nuxel/audio/audio.json.nuxel-rollback /etc/nuxel/audio/audio.json; systemctl restart nuxel-audio; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/audio/audio.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/audio/audio.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/audio/audio.json)"
if [ -e /etc/nuxel/audio/audio.json ] && [ ! -e /etc/nuxel/audio/audio.json.nuxel-rollback ]; then cp -a /etc/nuxel/audio/audio.json /etc/nuxel/audio/audio.json.nuxel-rollback; fi
test -f /etc/nuxel/audio/audio.json.nuxel-staged
printf '%s  %s\n' 2630cd0afa96737f82fdab262de68f84fea01df6096e9100fbd3a2778b0e0185 /etc/nuxel/audio/audio.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/audio/audio.json.nuxel-staged /etc/nuxel/audio/audio.json
sha256sum /etc/nuxel/audio/audio.json | grep -q 2630cd0afa96737f82fdab262de68f84fea01df6096e9100fbd3a2778b0e0185
systemctl restart nuxel-audio
systemctl is-active nuxel-audio
echo INSTALL-OK
