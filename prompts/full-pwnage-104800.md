# FULL-PWNAGE-104800 — Wi-Fi, networking, DNS and persistence

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104800.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Keep Wi-Fi and networking correct, performant and persistent: stable association,
DHCP, working DNS, sane MTU/power management, correct AP/repair behaviour, and a clean
recovery path when the access point disappears. SSH, VNC and XRDP all depend on it.

---

## 1. Current observed state (2026-11-14 16:02 CET)

```
NetworkManager      : active
wpa_supplicant      : active
wlan0               : UP, 192.168.178.167/24 (DHCP)
default via 192.168.178.1 dev wlan0 metric 600
DNS                 : resolves (fedora.org → 51.210.8.151)
also present        : ztly5zthnf (ZeroTier) 10.11.12.99, wlan1, P2P-device
                    : rmnet0..6 / umts_dm0 / mcps0 exist but DOWN (modem path)
ping(8)             : NOT installed
```

Existing reference: `REPORT-MOBILE-NETWORKING.md`, `full-pwnage-mobile.md`,
`full-pwnage-usbnet.md`, `configs/nuxel/*network*`, firewall policy in
`/etc/nuxel/firewall` and `remote-access.json`.

---

## 2. Non-negotiable rules

1. Never expose services on `0.0.0.0`; LAN listeners bind the WLAN address.
2. Do not change firewall/remote-access policy to "make SSH work" from an untrusted
   network.
3. Do not put Wi-Fi credentials in the repo, logs, or reports.
4. Bound every network test (timeouts); do not leave the radio in a scanning loop.

---

## 3. Work order

### Step 1 — Baseline

- Capture `nmcli device status`, `nmcli -f all con show`, `iw dev`, `iw link`,
  `ip -br addr`, `ip route`, `resolvectl status`, and `/etc/resolv.conf`.
- Record signal (RSSI/SNR), channel/band, bitrate, retries, and `iw dev wlan0 station dump`.
- Confirm DNS actually resolves and HTTPS works (`curl -sSI https://fedora.org`).

### Step 2 — Stability and power

- Check Wi-Fi power save (`iw dev wlan0 get power_save`) — must not cause stalls for
  SSH/VNC/RDP.
- Check roaming/reconnect when the AP drops (rename/disable AP or move out of range):
  must reconnect automatically and restore DHCP/DNS.
- Check IPv6 behaviour: ULA/GUA may be present; ensure it doesn't break SSH.

### Step 3 — Secondary interfaces

- `wlan1` and the `P2P-device` interface: are they intentional? They must not create
  duplicate/ambiguous routes.
- ZeroTier (`ztly5zthnf`): verify it doesn't hijack default routing or DNS.
- `rmnet*`/`umts_dm0`/`mcps0`: modem interfaces are DOWN — this is expected unless
  PWNAGE mobile (107000-family) is active; document, don't "fix" here.

### Step 4 — Persistence and recovery

- Reboot → association, DHCP, DNS, SSH, VNC, XRDP restore automatically.
- Provide a recovery procedure when the AP is gone (e.g. USB-net via
  `full-pwnage-usbnet.md` or console).

---

## 4. Report contract (`REPORT-PWNAGE-104800.md`)

Baseline captures, signal/throughput numbers, reconnect test, DNS/HTTPS evidence,
secondary-interface findings, reboot evidence, recovery procedure, rollback. End with
`FULLY_DONE` / `PARTIAL` / `BLOCKED`.
