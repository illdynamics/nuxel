# Nuxel security configuration (`/etc/nuxel/security/`)

This directory is the single source of truth for the **privacy surfaces** of a
Nuxel phone: VPN, Tor, remote access and the privacy daemon that the
`pwa/nuxel-apps/privacy` control centre reads.

| File | Consumed by | What it decides |
|---|---|---|
| `privacy-config.json` | `tools/s10plus/a33/nuxel-vpn-tor.sh`, `shell/nuxel-shell/nuxel-privacy/nuxel-privacyd.py` | Profiles, timeouts, bind addresses, default-off policy for remote access, and the claim vocabulary |
| `tor/torrc` | `tor.service` (`/etc/tor/torrc`) | Client-only Tor: SOCKS 9050, DNS 9053, TransPort 9040, control port 9051 with cookie auth, disk-write avoidance |
| `remote-access.json` | `nuxel-vpn-tor.sh remote`, the remote-access unit | Remote access is **off by default** and, when enabled, binds only to the owner console interface. NUXEL-26000 records the actual Tri-Link state there: WLAN key-only SSH is active; USB NCM is blocked by a kernel panic. |

## The truth ladder (why this directory exists)

Every privacy feature in Nuxel has *three* things that are easy to conflate:

1. **the process is running** (`tor.service` active, `wg` interface exists)
2. **the tunnel/circuit exists** (a built Tor circuit, a WireGuard handshake)
3. **traffic is actually going through it** (no leaks, real exit node)

Only (1) and (2) are observable from the device. (3) requires an external
vantage point. This repository therefore records them as three separate,
machine-readable claims and marks (3) `unproven` until someone produces
evidence - see `docs/beta-finalization/security/VPN-TOR-REMOTE.md` and manual
proof 21.

Nothing in this directory contains keys, passwords, bridge lines or exit-node
preferences for a specific person: VPN credentials are referenced by *file
path* (`/etc/nuxel/security/vpn/<profile>.key`, mode 0600 root) and never
stored here.
