#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf (service: None, risk: medium)
# staged source: configs/nuxel/time/60-nuxel-timesyncd.conf
# previous-hash: 952aee45b11db947b08be32ae5fdfcf296ee1ab9de44e7cf7046fbc03aa55302
set -eu
mkdir -p "$(dirname /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf)"
if [ -e /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf ]; then cp -a /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf.nuxel-rollback; fi
test -f /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf.nuxel-staged
printf '%s  %s\n' 952aee45b11db947b08be32ae5fdfcf296ee1ab9de44e7cf7046fbc03aa55302 /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf.nuxel-staged /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf
sha256sum /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf | grep -q 952aee45b11db947b08be32ae5fdfcf296ee1ab9de44e7cf7046fbc03aa55302
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf.nuxel-rollback ]; then cp -a /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf.nuxel-rollback /etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf; true; fi
