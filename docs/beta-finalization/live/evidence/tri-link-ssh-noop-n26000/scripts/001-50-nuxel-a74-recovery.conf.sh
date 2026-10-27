#!/bin/sh
# WLAN/USB SSH console (OpenSSH, public key only) -> /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf (service: sshd.service, risk: low)
# staged source: configs/nuxel/security/ssh/50-nuxel-a74-recovery.conf
# previous-hash: 97ac6bfebb400f3f44c2721e3b4661a469ee82d8d2316daa7058dc7ccce5973f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf.nuxel-rollback.pre-tri-link-ssh-noop-n26000 ]; then cp -a /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf.nuxel-rollback.pre-tri-link-ssh-noop-n26000 /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -x /usr/sbin/sshd
test -f /etc/ssh/sshd_config
if [ -e /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf ]; then printf 'PREV=%s\n' "$(sha256sum /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf)"
if [ -e /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf ] && [ ! -e /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf.nuxel-rollback ]; then cp -a /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf.nuxel-rollback; fi
if [ -e /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf ] && [ ! -e /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf.nuxel-rollback.pre-tri-link-ssh-noop-n26000 ]; then cp -a /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf.nuxel-rollback.pre-tri-link-ssh-noop-n26000; fi
test -f /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf.nuxel-staged
printf '%s  %s\n' 97ac6bfebb400f3f44c2721e3b4661a469ee82d8d2316daa7058dc7ccce5973f /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf.nuxel-staged /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf
sha256sum /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf | grep -q 97ac6bfebb400f3f44c2721e3b4661a469ee82d8d2316daa7058dc7ccce5973f
install -d -m 0700 -o nuxel -g nuxel /home/nuxel/.ssh
chown nuxel:nuxel /home/nuxel/.ssh/authorized_keys 2>/dev/null || true
chmod 0600 /home/nuxel/.ssh/authorized_keys 2>/dev/null || true
sshd -t
echo INSTALL-OK
