# PWNAGE-104200 — XRDP + VNC fixes, live evidence (2026-11-14 15:40–16:05 CET)

Host: 192.168.178.167 (root). Client: macOS + Jump Desktop; headless tests with
`sdl-freerdp` and a Python Apple-DH probe.

## 1. XRDP — root causes and fixes

1. `nuxel-remote-vnc-loopback` dead after compositor restart (`BindsTo` without
   `PartOf`). New drop-in:
   `/etc/systemd/system/nuxel-remote-vnc-loopback.service.d/60-p104-follow-wayland.conf`
   (`PartOf=nuxel-wayland.service`, `Restart=always`).
2. Stale `LoadCredential` config: `_install_xrdp_config()` returned early after
   writing `/etc/xrdp/xrdp.ini`, never updating
   `/var/lib/nuxel/remote-desktop/xrdp.ini`. Patched to always publish the staged copy.
3. libvnc local PAM failed: stored owner password no longer matched `nuxel`.
   Reset account password to the owner value; re-synced
   `/etc/nuxel/remote-desktop/xrdp/{owner-password,credential}`.
4. Note: empty `username=`/`password=` makes libvnc skip connecting entirely — kept
   `username=ask` / `password=ask`.

## 2. VNC — Apple DH framing (neatvnc fork)

`/root/nuxel-build/neatvnc/src/auth/apple-dh.c`:
- send real `mod_len` / `q_len` (the public key is shorter than 64 bytes),
- client frame is `creds[128] | be16(key_len) | key` — parse it.

Before: `Got uninterpretable message ... dump=10 00 07 1e ...`
After:  Apple-DH handshake succeeds, server init 720x1520.

## 3. Evidence

```
types [19, 129, 5, 30]           # vencrypt, rsa-aes256, rsa-aes128, apple-dh
gen 2 key_size 64
security result 0
SERVER INIT OK framebuffer 720 x 1520 name b'WayVNC'
PASS: Apple-DH auth + session init succeeded
```

XRDP (`/var/log/xrdp.log`):
```
[INFO ] Nuxel PAM auth ok for user nuxel
[INFO ] VNC: Clipboard supports ISO-8859-1 text only
```
Loopback (`journalctl -u nuxel-remote-vnc-loopback`):
```
Info: New client connection from ::1: ...
Info: Starting screen capture
```

## 4. Hashes (post-fix)

```
a156153821648376572709ace304b6daff9d42b9fd4f6ff533f68ec17f9849df  /opt/nuxel-wayvnc/lib64/libneatvnc.so.1.0.4
7e54f85e632e287fffba6ff96aba57c0b21154466cbf22de2477feb3a7e8ff7c  /root/nuxel-build/neatvnc/src/auth/apple-dh.c
780425fba48b1f5afd654978c9a69b441cbd450c36fed8007131561939316e2a  /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl
069e4008672f03ae3fd3e61a773556fc95d6e42204bfee13d2451ff8e7a1cb71  /var/lib/nuxel/remote-desktop/xrdp.ini
24eb148fb60e1e1ace4815a79a6bac31d2228ff7a3defbca33c421bbaa24a398  /etc/systemd/system/nuxel-remote-vnc-loopback.service.d/60-p104-follow-wayland.conf
```

Backups: `libneatvnc.so.1.0.4.bak-104000-*`, `xrdp.ini.bak-104000`,
`nuxel-remote-desktop-ctl.bak-104000-*`, `apple-dh.c.pre-104000`.

## 5. Open items

- GUI acceptance in Jump Desktop (`nux-vnc`, `nux-rdp`) still needs live human
  verification — see `full-pwnage-104200.md` §4.
- Owner password is now the documented value in `owner-password` / `credential`.
