# FULL-PWNAGE-104200 — Remote desktop: XRDP + VNC that actually stream

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Client under test:** Jump Desktop on macOS (profiles `nux-vnc`, `nux-rdp`)
**Report to produce:** `REPORT-PWNAGE-104200.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Make **both** remote-desktop paths usable from the Mac:

1. **VNC (TCP 5900)** — must connect and stay connected. Previously it
   authenticated and then instantly disconnected.
2. **XRDP (TCP 3389)** — must show live screen updates. Previously mouse control
   worked but the Mac showed no picture/updates.

Both must mirror the **real phone screen** (Phoc/Wayland session), accept
`nuxel` + the owner password, and survive a compositor restart and a reboot.

---

## 1. Architecture (as implemented — keep this shape)

```
Jump Desktop ──VNC 5900──▶ wayvnc (-C wayvnc.conf)  ──▶ Phoc HEADLESS-1 (720x1520)
Jump Desktop ──RDP 3389──▶ xrdp (TLS, xrdp-sesman PAM)
                              └─ libvnc.so ──VNC 5901(localhost)──▶ wayvnc (-C wayvnc-loopback.conf)
```

Key components:

| Path | File |
|---|---|
| VNC service | `nuxel-remote-vnc.service` → `/usr/libexec/nuxel/nuxel-vnc-wayland` |
| VNC config | `/etc/nuxel/remote-desktop/vnc/wayvnc.conf` |
| Loopback service | `nuxel-remote-vnc-loopback.service` → `/usr/libexec/nuxel/nuxel-vnc-loopback` |
| Loopback config | `/etc/nuxel/remote-desktop/vnc/wayvnc-loopback.conf` |
| XRDP live config | `/var/lib/nuxel/remote-desktop/xrdp.ini` (loaded as systemd `LoadCredential`) |
| XRDP generator | `/usr/local/libexec/nuxel/nuxel-remote-desktop-ctl` (`_write_xrdp_config`, `_install_xrdp_config`) |
| VNC library | `/opt/nuxel-wayvnc/lib64/libneatvnc.so.1.0.4`, sources in `/root/nuxel-build/neatvnc` |

`xrdp.service` loads `/run/credentials/xrdp.service/xrdp.ini`. **Editing
`/etc/xrdp/xrdp.ini` alone does nothing** — the credential copy is what runs.

---

## 2. Root causes found and fixed (2026-11-14 15:40–16:00 CET)

### 2.1 XRDP: "Error connecting to user session"

- `nuxel-remote-vnc-loopback` had `BindsTo=nuxel-wayland.service` without `PartOf`,
  so after the 14:55 compositor restart it stayed dead and `::1:5901` was refused.
- Fix: drop-in `/etc/systemd/system/nuxel-remote-vnc-loopback.service.d/60-p104-follow-wayland.conf`
  (`PartOf=nuxel-wayland.service`, `Restart=always`).

### 2.2 XRDP: stale credential config

- `_install_xrdp_config()` wrote `/etc/xrdp/xrdp.ini` and **returned early**, never
  updating the staged `LoadCredential` file. Restarts re-applied old settings.
- Fix (in the ctl): always write `XRDP_STAGE` (`/var/lib/nuxel/remote-desktop/xrdp.ini`)
  and the `/run/nuxel/remote-desktop/xrdp.ini` copy, then mirror to `/etc`.

### 2.3 XRDP: libvnc PAM failing

- xrdp's patched `libvnc.so` performs a **local PAM check** (`xrdp-sesman`) before it
  dials the loopback. It failed with `Nuxel PAM auth failed for user nuxel`.
- Cause: the stored owner password (`/etc/nuxel/remote-desktop/xrdp/owner-password`,
  dated Nov 9) no longer matched `nuxel`'s hash — `/etc/shadow` changed at 14:11 today.
- Fix: reset `nuxel` password to the owner value, re-sync `owner-password` and
  `credential`. Verify with the PAM harness (§4).
- Note: leaving `username=`/`password=` **empty** in `[Xorg]` makes libvnc skip the
  connect entirely. Keep `username=ask` / `password=ask`.

### 2.4 VNC: instant disconnect after auth

- Jump Desktop negotiates **Apple DH (security type 30)**. The Nuxel `neatvnc` fork
  mis-framed the client's response:
  - `apple_dh_send_public_key()` sent `mod[64]` + `q[64]` and a `key_size`, but the
    server public key `q` is shorter than 64 bytes — the length field lied.
  - `apple_dh_handle_response()` assumed `[128B creds][key]` with an implicit length,
    while the client sends `[128B creds][be16 key_len][key]`.
  - Result: `Got uninterpretable message ... dump=10 00 07 1e ...` → connection closed.
- Fix in `/root/nuxel-build/neatvnc/src/auth/apple-dh.c`:
  - send real `mod_len`/`q_len`,
  - parse the be16 key length, validate it, import the remote key correctly,
  - return the correct consumed length.
- Rebuilt with `ninja -C /root/nuxel-build/neatvnc/build`, installed to
  `/opt/nuxel-wayvnc/lib64/libneatvnc.so.1.0.4` (backup kept).

### 2.5 Why XRDP had no picture

- XRDP mirrors the Phoc output; with the loopback dead or libvnc not connected, only
  input/pointer was forwarded. Restoring §2.1–2.3 restored live frames.

---

## 3. Verification performed (repeat all of it)

```sh
# services + listeners
systemctl is-active xrdp xrdp-sesman nuxel-remote-vnc nuxel-remote-vnc-loopback
ss -lntp | grep -E '3389|5900|5901'
# 3389 on 192.168.178.167, 5900 on 192.168.178.167, 5901 on [::1]

# PAM harness (compiled from wayvnc's pam_auth logic)
/tmp/pamtest xrdp-sesman nuxel 'nuxel-remote'   # expect 0/0/0
/tmp/pamtest wayvnc     nuxel 'nuxel-remote'   # expect 0/0/0

# XRDP end-to-end from the Mac (sdl-freerdp, 25s)
sdl-freerdp /v:192.168.178.167:3389 /u:nuxel /p:'nuxel-remote' \
  /cert:ignore /size:720x1520 /timeout:10000 +auto-reconnect
# Phone log must show: "Nuxel PAM auth ok", loopback "New client connection",
# "Starting screen capture", and no disconnect until the timeout.
```

XRDP success signature in `/var/log/xrdp.log`:

```
[INFO ] Nuxel PAM auth ok for user nuxel
[INFO ] VNC: Clipboard supports ISO-8859-1 text only
```
and in `journalctl -u nuxel-remote-vnc-loopback`:
```
Info: New client connection from ::1: ...
Info: Starting screen capture
```

### VNC Apple-DH verification

Run the Apple DH harness in §6 against `192.168.178.167:5900` with
`nuxel` / `nuxel-remote`. Expect:

```
types [19, 129, 5, 30]
gen 2 key_size 64
security result 0
SERVER INIT OK framebuffer 720 x 1520 name b'WayVNC'
PASS: Apple-DH auth + session init succeeded
```

Also verify VeNCrypt: subtype reply must be `00000001` (X509Plain).

---

## 4. GUI acceptance (Jump Desktop — required)

1. Launch **Jump Desktop** (`open -a "Jump Desktop"`).
2. Open profile **`nux-vnc`** (192.168.178.167:5900, user `nuxel`).
   - Must connect and show the phone screen.
   - Move the mouse / type — the phone must respond.
   - Wait 60 s — the session must not drop.
3. Open profile **`nux-rdp`** (192.168.178.167:3389, user `nuxel`).
   - Must show the phone screen (not a blank window).
   - Mouse control must work **and** the picture must update (change screens
     on the phone / start an app and watch the Mac refresh).
   - Wait 60 s — no disconnect.
4. Reconnect both after closing — no stale-socket failures.

If Jump Desktop still drops, capture the phone-side log for that connection
(`journalctl -u nuxel-remote-vnc --since -2min` and `tail -50 /var/log/xrdp.log`)
and reopen §2 with the new evidence instead of guessing.

---

## 5. Constraints / non-goals

- Do not bind 0.0.0.0; listeners stay on the trusted WLAN address or `::1`.
- Do not disable PAM or TLS to "make it work".
- Do not give the loopback mirror a LAN address.
- Do not change the phone's panel mode from a client (resizing is rejected by design).
- Keep `ask/ask` in the `[Xorg]` session; empty values break libvnc's connect.
- Do not unbound `Restart=` loops; the loopback restart is already bounded.

---

## 6. Helper: Apple-DH test client

A minimal probe (Python + `cryptography`) that reproduces Jump's Apple DH handshake:

```python
# 1. read 12-byte banner, send b"RFB 003.008\n"
# 2. read 1-byte count + types; require 30 (apple-dh)
# 3. send b"\x1e"; read 4-byte (gen:be16, key_size:be16)
# 4. read key_size bytes modulus + key_size bytes server public key
# 5. derive DH secret; AES-128-ECB key = MD5(shared_secret_padded_to_key_size)
# 6. send AES(creds[128]) + be16(key_size) + client_public_key
# 7. read 4-byte security result; expect 0
# 8. send share flag 1; expect ServerInit 720x1520 "WayVNC"
```

Expected failure before §2.4 (documented): `uninterpretable message ... 10 00 07 1e`.

---

## 7. Report contract (`REPORT-PWNAGE-104200.md`)

Include: root causes, exact diffs (file + before/after), build/install commands,
service states, listener output, PAM harness output, Apple-DH probe output, Jump
Desktop screenshots for **both** profiles, and rollback commands
(`libneatvnc.so.1.0.4.bak-104000-*`, `xrdp.ini.bak-104000`,
`nuxel-remote-desktop-ctl.bak-104000-*`).

End with `FULLY_DONE` only if both Jump profiles stream live video **and** accept
input. Otherwise `PARTIAL`/`BLOCKED` with the exact evidence.

---

## 8. 104000 addendum — VNC drops instantly, XRDP shows no picture

Measured 2026-11-14 16:25 CET (re-verify):

```
xrdp 0.10.6.1-3.fc43 + xorgxrdp 0.10.5-1.fc43   LISTEN :3389
tigervnc-server: NOT INSTALLED
wayvnc  pid 124873  LISTEN 192.168.178.167:5900
wayvnc  pid 125304  LISTEN [::1]:5901
xrdp[178749]: ERROR Error connecting to user session
xrdp[178749]: ERROR SSL_read: Failure in SSL library (protocol error?)
              error:0A000126:SSL routines::unexpected eof while reading
```

Also note: **`/dev/dri` does not exist** on the phone. Many clients drop a VNC/RDP
session whose framebuffer never changes or whose capture path falls back to a
slow/blocking grabber. Fix graphics first (104700) if the pixmap path depends on
DRM; until then use the headless compositor's software capture explicitly.

### Work order

1. **VNC instant-quit**: run `wayvnc -C <conf>` in the foreground with `-L debug`
   and connect with `vncviewer`/Jump Desktop; capture the disconnect reason. Check
   auth method (VeNCrypt vs Apple-DH vs RFB), TLS cert, `pam_service`, and the
   `xkb`/keymap load. A missing `/dev/dri` must not abort capture — verify
   `wayvnc` is built with the CPU-capture fallback.
2. **XRDP no picture**: `xorgxrdp` sessions need a working X/backing framebuffer.
   Inspect `/var/log/xrdp-sesman.log`, `~nuxel/.xorgxrdp.*.log`,
   `/etc/xrdp/xrdp.ini` (`[Xorg]` vs `[Xvnc]`), and `libvnc.so` loopback target.
   Confirm GFX/H.264 path and that the RDP backend actually pushes frames
   (compare with `xrdp-sesman` frame stats).
3. **Credentials** (both protocols): user `nuxel`, password `Enf0rcer#.nux`.
   - `useradd`/`usermod` state, `chpasswd`, PAM (`/etc/pam.d/xrdp-sesman`,
     `vnc` service), `xrdp-sesman.ini` `[Security]`/`[Sessions]`.
   - Do **not** store the cleartext password in repo files; if needed on disk only
     as root-only 0600, and never in logs.
4. **Jump Desktop profiles** `nux-rdp` / `nux-vnc` saved on the Mac with host
   `192.168.178.167`, ports 3389/5900, user `nuxel`, and the working credential.
   Export/record the settings (screenshot) to `evidence/pwnage-104000/jump/`.

### Acceptance (all required, from Jump Desktop)

- [ ] RDP: login succeeds; window shows the **live phone screen**; moving the
      mouse on the Mac moves the pointer on the phone; typing works.
- [ ] VNC: connects and **stays** connected ≥ 5 min while the phone is used;
      live updates; input works.
- [ ] Both survive a `wayvnc`/`xrdp` restart **and** a phone reboot.
- [ ] No cleartext password in repo, logs or screenshots.
