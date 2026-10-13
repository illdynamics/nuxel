# NetworkManager privacy defaults (briq-15 / briq-se1)

These files install into the network stack to make Nuxel privacy defaults *real*,
not aspirational:

| File | Install to | Purpose |
|------|-----------|---------|
| `98-nuxel-defaults.conf` | `/etc/NetworkManager/conf.d/` | MAC randomization for every WiFi connection + device scan |
| `98-nuxel-dns.conf` | `/etc/NetworkManager/conf.d/` | Prefer private DNS (`dns-priority=-1`), DM to encrypted stub |
| `resolved-conf.d/nuxel-privacy.conf` | `/etc/systemd/resolved.conf.d/nuxel-privacy.conf` | **Actual** DoH/DoT transport (pinned Cloudflare upstreams + `DNSOverTLS`) — Fedora/VM |
| `nuxel-stubby.yml` | `/etc/stubby/stubby.yml` | DoT/DoH stub for mustang / pure-OpenRC (no systemd) |

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
