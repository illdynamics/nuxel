# PWNAGE-47000 — deployment and rollback manifest

_Live target: S10+ SM-G975F, `beyond2lte`, kernel `4.14.253-gf7194c1d15ed-dirty`._
_Host: macOS 15.7.9 (24G830 arm64), Jump Desktop 9.1.21._

## Deployed files (live phone)

| Path | Purpose | Mode |
|---|---|---|
| `/etc/systemd/system/nuxel-remote-vnc.service` | on-demand wayvnc unit (loopback) | 0644 |
| `/usr/local/libexec/nuxel/nuxel-remote-desktop-ctl` | fixed-argv start/stop/status helper | 0755 |
| `/usr/lib/nuxel/nuxel-bridge/remote_desktop.py` | `system.remote-desktop` provider | 0644 |
| `/etc/nuxel/remote-desktop/vnc/wayvnc.conf` | generated loopback RFB config | 0644 |
| `/etc/xrdp/xrdp.ini`, `sesman.ini`, `xorg-nuxel.conf` | loopback TLS RDP + separate Xorg | 0644 |
| `/usr/local/bin/nuxel-xrdp-session` | Openbox + Firefox kiosk launcher | 0755 |
| `/etc/nuxel/remote-desktop/xrdp/credential` | unique `nuxel-remote` password | **0600 root:root** |
| `/etc/xrdp/nuxel-cert.pem`, `nuxel-key.pem` | per-image TLS material | 0640 xrdp group |
| `/etc/selinux/config` | `SELINUX=permissive` boot guard | 0644 |
| `/etc/group` gid 3003 `inet` | `nuxel`, `nuxel-remote` members | system file |

No boot enablement was created for `nuxel-remote-vnc.service`, `xrdp.service` or
`xrdp-sesman.service`. Both services were verified OFF after a reboot.

## Repository changes

- `services/nuxel-bridge/src/remote_desktop.py`
- `services/nuxel-bridge/src/api.py` (namespace/route)
- `services/nuxel-remote-desktop/` (ctl, session, units, configs, launcher)
- `services/nuxel-bridge/systemd/nuxel-http-bridge.service`
- `pwa/nuxel-apps/remote-xrdp/`, `remote-vnc/`, `remote-scrcpy/`
- `pwa/nuxel-common/{app-registry.json,remote-desktop.js,remote-desktop.css,bridge.js}`
- `pwa/nuxel-home/{index.html,sw.js,manifest.json,js/apps.js,css/status-bar.css,js/status-bar.js}`
- `shell/nuxel-home-native/nuxel_home/app_registry.json`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`, `packages-manifest.json`
- `configs/nuxel/security/remote-access.json`, `configs/nuxel/security/ssh/{60,62}-*.conf`
- `tests/a80/test_remote_desktop.py`
- `scripts/nuxel-scrcpy.sh`, `scripts/nuxel-gui-tunnel.sh`
- `GUI-TRI-LINK-QUICKSTART.md`, this file, `PWNAGE-47000-TODO.md`, `PWNAGE-47000-REPORT.md`

## Mac-side state

- `nux-vnc` Jump profile: VNC `127.0.0.1:15900`, no saved password.
- `nux-rdp` Jump profile: RDP `127.0.0.1:13389`, no saved password.
- Pinned SSH known-host remains `SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs`.
- Host key files are read-only inputs; no private key was copied to the phone.

## Rollback (phone)

```sh
# 1. Stop and close both listeners (safe kill switch).
sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl stop-all

# 2. Make sure nothing can re-activate at boot.
sudo -n systemctl disable --now xrdp.service xrdp-sesman.service 2>/dev/null || true
sudo -n systemctl disable --now nuxel-remote-vnc.service 2>/dev/null || true

# 3. Remove only the PWNAGE-47000 remote-desktop files.
#    (Keep sshd, serial, Phoc, nuxel-wl-fb and the physical session untouched.)
sudo -n rm -f /etc/systemd/system/nuxel-remote-vnc.service
sudo -n rm -f /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl
sudo -n rm -rf /etc/nuxel/remote-desktop
sudo -n rm -f /usr/local/bin/nuxel-xrdp-session
sudo -n rm -f /usr/lib/nuxel/nuxel-bridge/remote_desktop.py

# 4. Restore the Bridge module / registry from the pre-47000 backup and restart
#    only the Bridge.  Never reboot or kill Phoc to "fix" a remote service.
sudo -n systemctl restart nuxel-http-bridge

# 5. Keep the boot guards: /etc/selinux/config must stay permissive and the
#    nuxel/nuxel-remote accounts must stay in gid 3003 (inet) on this kernel.
```

## Recovery guarantees

- Serial CDC-ACM console and WLAN SSH remain independent of every GUI service.
- Do not retry NCM, mutate configfs or rebind the UDC. USB RDP/VNC remains
  `BLOCKED_KERNEL_PANIC` on 4.14.253.
- If VNC/XRDP destabilizes the phone, stop only those services; do not touch
  Phoc, `nuxel-wl-fb`, `/dev/fb0`, sshd or the serial gadget.
