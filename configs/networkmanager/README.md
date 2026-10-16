# NetworkManager privacy defaults (briq-15 / briq-se1)

These files install into the network stack to make Nuxel privacy defaults *real*,
not aspirational:

| File | Install to | Purpose |
|------|-----------|---------|
| `98-nuxel-defaults.conf` | `/etc/NetworkManager/conf.d/` | MAC randomization for every WiFi connection + device scan |
| `98-nuxel-dns.conf` | `/etc/NetworkManager/conf.d/` | Prefer private DNS (`dns-priority=-1`), DM to encrypted stub |
| `resolved-conf.d/nuxel-privacy.conf` | `/etc/systemd/resolved.conf.d/nuxel-privacy.conf` | **Actual** DoH/DoT transport (pinned Cloudflare upstreams + `DNSOverTLS`) — Fedora/VM |
| `nuxel-stubby.yml` | `/etc/stubby/stubby.yml` | DoT/DoH stub for mustang / pure-OpenRC (no systemd) |
| `10-nuxel-s10plus-wifi.conf` | `/etc/NetworkManager/conf.d/` | S10+ Wi-Fi bring-up policy (wpa_supplicant backend, scan MAC randomization, power-save off during bring-up) |
| `wpa_supplicant-s10plus.conf` | `/etc/wpa_supplicant/` (owner-installed) | world regulatory domain (no invented country), `update_config=0`, no legacy `driver=` pin |
| `nuxel-s10plus-wifi.nmconnection.example` | nowhere (inert) | credential-free connection template; the `.example` suffix keeps NetworkManager from loading a placeholder profile |
| `nuxel-network-settings.spec.json` | repository contract only | the native Network Settings feature set + the `read_api` command behind every row (append point for briq-06d) |

## Wi-Fi diagnostics and evidence (briq-03a)

`tools/s10plus/a33/nuxel-wifi-diag.sh` (also `nuxelctl wifi …`) reports what the
live kernel, firmware directory and NetworkManager actually show, and never
claims a working radio: `status`/`scan`/`connect`/`disconnect`/`regdom`/
`firmware`, plus `mark` → one normal reboot → `compare` for **reconnection across
a reboot** (a pair with an unchanged boot id is REFUSED as evidence) and
`fallback` for the **no-cellular-fallback** policy audit. `settings-spec` prints
the network settings contract. Owner procedure:
`docs/beta-finalization/manual-proof/04-wifi.md`.

## DNS transport
`98-nuxel-dns.conf` sets `dns=systemd-resolved` (Fedora VM) and a negative
`ipv4/ipv6.dns-priority` so the local stub at `127.0.0.53` / `::1` wins.
The encryption itself is carried by the **shipped** `resolved-conf.d/nuxel-privacy.conf`
drop-in (or `nuxel-stubby.yml` on OpenRC). The VM bootstrap
(`vm/nuxel-vm-bootstrap.sh`, owned by the bg-vm group) already installs the two
`98-nuxel-*.conf` files; the resolved drop-in can be installed in the same stage.

## MAC randomization
Randomizing the MAC per-SSID defeats tracking across networks. A connection can
opt out by setting `wifi.cloned-mac-address=permanent`.
