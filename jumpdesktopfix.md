# Jump Desktop and direct Nuxel remote access

_Executed and verified 2026-10-31 on the MacBook and the Nuxel S10+._

## Result

| Item | Value |
|---|---|
| Phone IPv4 | `192.168.178.167` (`wlan0`, DHCP) |
| `nux-vnc` Jump profile | `192.168.178.167:5900`, VNC, **no SSH tunnel** |
| `nux-rdp` Jump profile | `192.168.178.167:3389`, RDP, **no SSH tunnel** |
| RDP login | local `nuxel` account, password `enf0rcer` |
| RDP TLS certificate | self-signed; SHA-256 `04:8C:7B:9F:ED:CA:2B:ED:97:D0:B5:68:E9:23:3D:B8:D6:AB:75:79:99:D0:02:AC:14:03:5B:FF:77:A4:E4:5D` |
| SSH administration | `nuxel@192.168.178.167` with `~/.ssh/wicked_wqn_id_rsa` |
| VNC server | `wayvnc`, listening on `0.0.0.0:5900` |
| RDP server | `xrdp`, listening on `0.0.0.0:3389`, TLS 1.2/1.3 |
| Current `nuxel-remote` credential | `EjImAosIRBoS9PhI3gaVRysrqwXa` (retired from the Jump profile) |
| Services at boot | Not enabled; they are on-demand |

## What was changed

- Both Jump `.jump` profiles were edited while Jump Desktop was quit:
  `TcpHostName=192.168.178.167`; `nux-vnc` port `5900`, `nux-rdp` port `3389`;
  `SshServerUniqueId=null`.
- Old `127.0.0.1` tunnel ports (`15900`/`13389`) and the stale xrdp certificate
  pin were removed from the profiles.
- `xrdp` now listens directly on `0.0.0.0:3389`, still with TLS and PAM.
- The xrdp session launcher was moved to the local `nuxel` HOME. RDP therefore
  logs in as the same identity as SSH/VNC (`/home/nuxel`), not `nuxel-remote`.
- `nuxel` was unlocked with password `enf0rcer` so RDP/PAM can authenticate it.
- `wayvnc` now listens on `0.0.0.0:5900` with `enable_auth=false`.

## Login credentials

- RDP: username `nuxel`, password `enf0rcer` (local phone account).
- VNC: no password.
- SSH: username `nuxel`, key `~/.ssh/wicked_wqn_id_rsa` (no SSH password).

## VNC caveat (important)

Jump Desktop 9.1.21 does not negotiate the authentication that wayvnc 0.9.1
offers on this image:

- Jump requests Apple DH (security type 30); wayvnc 0.9.1 does not support it.
- Jump does not accept wayvnc's RSA-AES types 5/129.
- Jump does not accept wayvnc's VeNCrypt subtype X509Plain.
- This Fedora wayvnc build no longer offers VNC password (DES) auth.

Therefore direct VNC is **unauthenticated** (`enable_auth=false`). It must be
restricted to the trusted owner LAN and later ZeroTier. Do not forward TCP
5900 to the Internet. RDP remains authenticated and encrypted.

VNC mirrors the real Phoc/Wayland phone screen. RDP is a separate X11 session
(Openbox + Firefox launcher) and does not mirror the physical phone screen.

## Verified

- Jump Desktop connected VNC to `192.168.178.167:5900` without an SSH forward:
  `RFB 003.008`, `WayVNC`, 720x1520.
- Jump Desktop connected RDP to `192.168.178.167:3389` without an SSH forward:
  TLS 1.3, PAM accepted `nuxel`, and the RDP session started with Xorg `:10`,
  `xrdp-sesexec` and Firefox under `/home/nuxel`.
- The `nuxel` RDP identity is stored in the profile as
  `UsernameCode = bnV4ZWw=` (base64 of `nuxel`).
- `ss -ltn` on the phone showed `0.0.0.0:5900` and `0.0.0.0:3389`.
- The phone was rebooted at the end and both services were checked again over
  Wi-Fi SSH with the requested key.

## Operational commands

```sh
ssh -i ~/.ssh/wicked_wqn_id_rsa nuxel@192.168.178.167 \
  'sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl status'

ssh -i ~/.ssh/wicked_wqn_id_rsa nuxel@192.168.178.167 \
  'sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl start vnc'

ssh -i ~/.ssh/wicked_wqn_id_rsa nuxel@192.168.178.167 \
  'sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl start xrdp'

ssh -i ~/.ssh/wicked_wqn_id_rsa nuxel@192.168.178.167 \
  'sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl stop-all'
```

If the phone's DHCP address changes, update `TcpHostName` in both Jump profiles
(Jump Desktop must be quit while editing the `.jump` files) or reserve the
lease in the router. ZeroTier access will use the phone's ZeroTier address in
the same two fields.
