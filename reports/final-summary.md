# Nuxel — Component Status Summary

- **Device:** Samsung Galaxy S10+ (SM-G975F, `beyond2lte`, Exynos 9820), board `BEYOND2LTE EUR OPEN 26`
- **Kernel:** `4.14.253-gf7194c1d15ed-dirty` (SMP PREEMPT aarch64), custom Nuxel build
- **Userland:** Nuxel "Mobile Linux for Control Freaks" on a Fedora-style root; Wayland/phoc compositor, PipeWire 1.4.11, systemd, NetworkManager, Flatpak 1.16.6
- **Live build:** `v0.8.5-beta` userspace (`NUXEL_BRIDGE_VERSION=0.8.5-beta`) — this document describes the **v0.8.5-beta** update deployed to it
- **Access used:** SSH `root@192.168.178.167` (key `~/.ssh/wicked_wqn_id_rsa`) over Wi-Fi **and** USB-ECM `root@10.15.19.1`
- **Survey date:** 2026-11-15
- **Legend:** ✅ Works · 🟡 Partial (kernel/transport ready, no complete userspace path) · ❌ Not working

> Every statement below was read from the running device (sysfs, `/proc`, systemd,
> dmesg, provider JSON) on 2026-11-15. The USB console link was used as the
> out-of-band path while Wi-Fi was being worked on.

---

## Quick overview

| Component | Status | Short reason |
|---|---|---|
| Wi-Fi uplink + SSH | ✅ Works | `wlan0` 192.168.178.167/24, DHCP, key-only SSH (firewall + sshd allowlist) |
| USB networking (ECM) | ✅ Works | `usb0` 10.15.19.1/24, SSH over USB verified from the Mac |
| USB tethering (shared Internet) | 🟡 Partial | Forwarding/NAT fixed; Mac-side scoped-route limits the owner's off-link test |
| Hotspot (`NuxNet`) | ✅ Works | hostapd + dnsmasq on `wlan1`, NAT on `wlan0`, `ip_forward=1` |
| Flatpak sandbox | ✅ Works | root-owned `/run/user/1000/.flatpak` was blocking every app; fixed |
| Flatpak audio / microphones | ✅ Works | Pulse socket now mapped at `/run/flatpak/pulse/native`; `parec` verified in-sandbox |
| Stremio | ✅ Starts | Registry unblocked + single-instance guard; sandbox verified |
| GTK/Flatpak app icons | ✅ Single icon | fallback glyph and coloured tile no longer painted behind external icons |
| Lock screen | ✅ | transient OSD/power-menu rectangle hidden on lock |
| Idle CPU | ✅ Improved | PCIe(DeX) suspend storm stopped; softirq 2000 → ~0 ticks |
| NFC | 🟡 Partial | Controller + NCI + daemon present; **no `/dev/nfc0`**, radio OFF, scan untested |
| Sensors / auto-rotate | ❌ Not working | BCM47752 hub powered but not streaming (`0,0,0`); Auto refused |
| Fingerprint | ❌ Not working | QBT2000 driver bound, but no device node, no libfprint/fprintd |
| Camera | ❌ Not working | Full FIMC-IS V4L2 stack present (68 nodes), no working userspace camera path |
| Mobile networking | ❌ Not working | Modem OFFLINE, `mmcli` "No modems found", `rmnet0` down |
| GPS | ❌ Not working | GNSS transport only; sensor hub never streams, position RPC missing |

---

## 1. Wi-Fi, SSH and USB console — ✅ Works

- `wlan0` `192.168.178.167/24`, default route via `192.168.178.1`, DHCP.
- `sshd` key-only; `nuxel_app_firewall` input chain accepts TCP/22 from RFC1918
  (the v0.8.3 live fix) and `sshd.service.d/20-nuxel-lan-allow.conf` keeps the
  LAN allowlist self-healing.
- USB console/SSH: `usb0` `10.15.19.1/24` (ECM gadget next to the ACM console),
  reachable at `root@10.15.19.1`. **Verified from the Mac during this session**
  (`ping` 10.15.19.1 and SSH both work, independent of Wi-Fi).
- The hostname is a 36-character IPv6-derived string (`2001-1c00-…`). This is
  legal but has two consequences recorded below (Flatpak instance ids, log noise).

## 2. USB tethering — 🟡 Partial (phone side fixed, host-side test limited)

**Fixed in v0.8.5:**
- `nuxel_app_firewall` forward chain had `policy drop` and an *empty* rule set; it
  ran at priority −100, i.e. **before** the tether table (−50), so no forwarded
  packet from the attached host was ever accepted. It now accepts the tether /
  hotspot interfaces and subnets, and the drop-log is the **last** rule (it used
  to sit first and shadow the accepts).
- `net.ipv4.ip_forward` was `0`: the tether provider restored the value it saw at
  start (0 after an earlier stop), silently disabling forwarding for both USB
  tethering and the hotspot. It is now durable in
  `/etc/sysctl.d/90-nuxel-tether.conf`, and tether `stop` no longer clobbers a
  running AP.
- `usb_tether.start()` now sets loose reverse-path filtering (`rp_filter=2`) on
  the tether and uplink interfaces (strict mode 1 black-holes forwarded replies).

**Verified:** `usb0` link, ICMP to `10.15.19.1`, `curl` from the phone to the
Internet, `ip_forward=1`, and the forward/NAT counters increment.

**Known limitation (not a phone fault):** macOS keeps `10.15.19.0/24` scoped to
`en12`; an off-link test (`curl --interface en12 1.1.1.1`) is refused by the Mac
(`No route to host`) before a packet leaves the host. The phone's forwarding
path is proven by the counters and by `ping`/`curl` through the AP/NAT path; a
host-side split default route is the remaining owner step for a full Mac test.

## 3. Hotspot (`NuxNet`) — ✅ Works

- `hostapd` (WPA2-PSK, channel 6, country NL) on **`wlan1`** (second vif), the
  uplink stays on `wlan0` — the owner's Wi-Fi connection is never disturbed.
- `dnsmasq` bound to `wlan1` only: DHCP `10.42.0.10–200`, DNS, lease file
  in `/run/nuxel-hotspot/`.
- AP `NuxNet` / password `Setyup34#` is up; state reports
  `state=on, ip_forward=true, dhcp=dnsmasq`.
- NAT: the kernel has **no** `nft` NAT chain support, so NAT lives in the
  dedicated `iptables` chain `NUXEL_HOTSPOT_NAT`/`NUXEL_HOTSPOT_FWD`; the helper
  reports this honestly (`nat_error` explains the fallback).
- The app-side Network Manager provider no longer calls
  `nmcli device wifi hotspot` (that path cannot work on this image — no udev, so
  NetworkManager never sees the phy): it now calls `/usr/libexec/nuxel/nuxel-hotspot`.

## 4. Flatpak apps, Stremio and microphones — ✅ Works

**Root cause of "Stremio won't start" and the broken messenger mic:** Flatpak's
per-instance runtime directory `/run/user/1000/.flatpak` was owned by **root:root**
(a helper created it as root). Flatpak as uid 1000 then died with
`Unable to lock …/.flatpak/<app>/.ref: Permission denied` before any app could
start. Ownership is now enforced for the session user at boot and at every
launch.

**Microphone ("sped-up robot" in WhatsApp/Ferdium, no mic in Signal):**
- Each Flatpak declares `--socket=pulseaudio`; its runtime creates an **empty,
  private** `/run/flatpak/pulse` and exports `PULSE_SERVER` to that path.
- The launcher's `--filesystem=/run/user/0/pulse:/run/flatpak/pulse` was invalid
  for Flatpak 1.16 (`Unexpected filesystem suffix … ignoring`) → nothing was
  mounted → the app recorded from a dead socket.
- The launcher now maps the live session Pulse socket onto the path the runtime
  advertises:
  `--filesystem=/run/nuxel-wayland/pulse`, `--filesystem=/run/flatpak/pulse`,
  `--filesystem=/run/flatpak/pulse/native`.
- **Verified on device:** with the launcher's exact argv, `parec` inside the
  sandbox streamed 393 KB from the S10+ microphone and `pactl info` answered.

**Stremio:** the registry entry was still marked `status: "unsupported"` with the
old `CONFIG_USER_NS=n` rationale (user namespaces actually work:
`unshare -Ur true` succeeds as uid 1000). It is now `supported`, and the wrapper
refuses a second instance (Stremio aborts with `EADDRINUSE :11470` on a duplicate
launch). Signal gained the same single-instance guard.

## 5. Idle CPU, smoothness — ✅ Improved

- **PCIe (DeX/HDMI-over-USB-C) suspend storm:** the Broadcom `dhdpcie` link
  (`14E4:4475`) was re-linking ~4×/second (≈39 suspend/resume cycles per 10 s)
  with no cable attached, burning softirq on every core. A device remove+rescan
  of `0000:01:00.0` ended the loop: **0 cycles in 4 s afterwards**, softirq went
  from ~2000 ticks/10 s to **27**, kernel log from ~3200 lines/s to ~0.
- System CPU while idle dropped from ~40 % (load 13+) to **~12 % busy, 89 %
  idle**; the residial load average comes from Samsung TZ/RPMB kthreads parked
  in `wait_woken` (harmless, kernel-side).
- Stale debug nftables tables (`inet dbg`, `inet t1`) left by an earlier session
  were removed.
- Launcher/drawer: per-icon inline `onload`/`onerror` handlers (re-compiled for
  every tile on every drawer/Home rebuild) replaced by one delegated listener;
  per-tile inline background styles replaced by a CSS custom property; icon
  sweeps deferred to a single rAF; external icon wells no longer paint a
  coloured tile.
- Settings: pattern-editor drop-shadow filter removed (software rasterizer
  re-filtered the full editor per pointer move) and replaced by a static glow
  under-stroke; background polling only while the page is visible.
- The display bridge runs the UI at 20 fps (software scanout) — this is the
  remaining ceiling for animation smoothness; the compositor has no usable GPU
  render node path on this kernel.

## 6. GTK/Flatpak app icons — ✅ Single icon

The "second icon drawn behind the real one" was the launcher's fallback glyph
(emoji or Nuxel tile) painted as a sibling behind the real icon. Every Adwaita /
Flatpak SVG is partly transparent, so the glyph showed through. Now:
- icon wells carry `data-icon-origin` (`gtk` / `flatpak` / `nuxel` / `pwa`);
- for external icons the fallback glyph is **structurally unpaintable**
  (CSS `display:none`, node removed after decode) and the coloured backdrop is
  dropped;
- verified in a headless render against the real launcher CSS/assets: external
  icons render a single image with a transparent well; Nuxel/PWA tiles keep
  their glyph and tint.

## 7. Lock screen — ✅ (transient rectangle removed)

The fixed top-centre overlay (`#nuxel-osd`: blue border + blue progress bar) and
the power-menu card are now hidden on any lock transition (`nuxel:lockscreen-shown`,
`nuxel:lock`, `visibilitychange`) and cannot paint while the lock glass is up
(CSS backstop on `body.lockscreen-active`). The native `nuxel-osd`/power menu
already closes its menu before running the lock action.

> Delivered frame note: the live frame captured during this session shows the
> stock lockscreen with its normal clock; the transient rectangle was not
> reproducible on demand, so the fix is defensive (hide on every lock path).

## 8. NFC — 🟡 Partial

- Kernel: `CONFIG_NFC`, `NFC_NCI`, `NFC_S3FWRN5`, `NFC_S3FWRN5_I2C`, `SEC_NFC`.
- S3NRN82 controller bound at **i2c-7 0x27** (`/sys/bus/i2c/devices/7-0027`),
  `/sys/class/nfc/nfc0` + `rfkill0` present, **not** blocked.
- `nuxel-nfcd.service` **active**; state `state=OFF, kernel_nci=true,
  last_tag_present=false, payment_supported=false`.
- **Missing:** no `/dev/nfc0` misc device, radio never enabled, no successful
  scan. Firmware blob `sec_s3fwrn5_firmware.bin` is present.
- To finish: expose/verify the NCI char device (nfc core `nfc_dev` registration +
  udev node `root:nuxel 0660`), enable the radio through `nuxel-nfcd`
  (rfkill unblock + s3fwrn5 firmware download), grant an app permission, run a
  real tag scan and confirm `last_tag_present` flips.

## 9. Sensors for auto-rotate — ❌ Not working

- Chips bound and 33 IIO devices exist: `LSM6DSO` (accel/gyro), `LPS22H`,
  `AK09916C`, `TCS3407`, `MAX86917`, `TMD4910`, `SX9330`.
- The BCM47752 sensor hub is **powered but not streaming**
  (`enable_bits=0`, `raw_data="0,0,0"`, `raw_live=false`, no LHD patch loader).
- `nuxel-orientationd` runs (`_daemon_live=true`) but reports
  `sensor.available=false`, `auto_state="fixed"`; Auto is refused, not faked.
- Mount matrix and gravity reference are `unverified` (no gravity to calibrate).
- To finish: install the Broadcom LHD sensor-hub patch loader + firmware for
  BCM47752KUB1G and bring the hub up so the accel streams; then calibrate the
  mount matrix against the panel and enable Auto. (Alternatively drive rotation
  from a separately validated IIO accelerator — blocked today because the IIO
  accel path also reads zero and has no scale.)

## 10. Fingerprint — ❌ Not working

- Driver active: `qbt_finger_detect` IRQ, `/sys/class/fingerprint/fingerprint/`
  exposes `QBT2000` (vendor QCOM), TZ up (`tz:1`), but LDO/IPC off.
- **No** `/dev/fingerprint` (or any char/misc node) for userspace.
- **No** `libfprint`, **no** `fprintd`; `nuxel-fingerprintd.service` inactive.
- To finish: a userspace protocol for QBT2000 (upstream libfprint has none) that
  powers LDO/IPC and talks to the TEE TA, a libfprint driver + `fprintd` + udev
  perms (`root:fprint 0660`), then enroll/verify and wire `pam_fprintd`.

## 11. Camera — ❌ Not working

- The kernel media stack is fully bound: 68 `/dev/video*` nodes, all
  `exynos-fimc-is-*` (ss0–ss5, 30/31/i0/i1 sensor subdevs, `-30c/-31c/-i0c/-i1c`
  capture, `me0c/me1c`), `s5p-mfc` decode/encode, `exynos-jpeg`,
  `/sys/class/camera/{rear,front,ois,flash}` and the rear flash LED sysfs.
- **No working userspace path**: the native camera helper exists
  (`/usr/lib/nuxel/nuxel-camera-native`) but `nuxel-camera-portal.service` is
  inactive and no app capture has been demonstrated on the live image.
- To finish: a validated FIMC-IS capture sequence (sensor subdev → ISP → capture
  node) including the vendor ISP setfiles for the bound sensors, power-on
  sequencing and the TEE/secure-camera handshake, then bridge it to the camera
  portal + app.

## 12. Mobile networking — ❌ Not working

- Modem `s5000ap` OFFLINE; `mmcli -L` → "No modems were found"; `rmnet0` (and
  rmnet1–7) `DOWN`; ModemManager active but with no device.
- No SIM/carrier state, no data bearer, no SMS/call path.
- To finish: modem firmware/boot handshake for the CP (BP boot + `ss310ap`/`rmnet`
  bring-up), then ModemManager recognition, APN/bearer and `rmnet` data.

## 13. GPS — ❌ Not working

- GNSS transport exists, but position depends on the same BCM47752 hub that
  never streams, plus a proprietary position RPC map that is absent.
- To finish: same hub bring-up as §9, then the GNSS LHD service and a real fix.

---

## Dependency map

```
BCM47752 sensor hub (not streaming) ─┬─ auto-rotate / orientation
                                     ├─ gyroscope, step/context sensors
                                     └─ GNSS position
QBT2000 TEE protocol (missing) ──────── fingerprint enroll/verify
FIMC-IS capture sequence (missing) ──── camera
CP/modem boot (offline) ─────────────── mobile data, SMS, calls
NFC nfc0 char node (missing) ────────── tag scan / write
```

## Suggested priority order

1. **Auto-rotate** (BCM47752 LHD hub) — unlocks §9 and §13 and the gyroscope.
2. **NFC char node + radio enable** — close but needs the NCI node and a scan.
3. **Camera** — most kernel work is done; needs the capture/ISP sequence.
4. **Fingerprint** — largest unknown (vendor TEE protocol).
5. **Mobile networking** — CP firmware/boot, then ModemManager.
