# Nuxel Firewall — architecture, backend matrix and recovery

## Status
- **Implemented**: canonical policy model + privileged provider + backend
  adapters + PWA app + Settings/Quick Settings integration + CLI + tests.
- **Live device (S10+, Linux 4.14.253-gf7194c1d15ed-dirty)**: the kernel does
  **not** enable nftables (`CONFIG_NF_TABLES is not set`) and does **not** enable
  the xtables cgroup match (`CONFIG_NETFILTER_XT_MATCH_CGROUP is not set`).
  Classic xtables/iptables (IPv4 + IPv6) is built in, and `owner` match is
  available. No `nft`/`iptables`/`ufw`/`firewalld` binaries are installed.

## Policy defaults (owner request)
| Direction | Default | Meaning |
|---|---|---|
| INPUT | deny | Unsolicited inbound denied; SSH/XRDP/VNC are explicit, source-restricted. |
| FORWARD | deny | No routing/tethering unless an explicit forwarding profile enables it. |
| OUTPUT | allow | Outbound allowed by default; per-app/global strict deny is configurable. |

The canonical model is `configs/nuxel/firewall/policy.json` (schema
`policy.schema.json`, validator `services/nuxel-firewall/nuxel_firewall/schema.py`).

## Backend matrix
| Backend | Kernel support (S10+) | Global direction | Per-app matrix |
|---|---|---|---|
| `iptables` (xtables) | Yes (built-in IPv4+IPv6, owner match) | Yes | Only with distinct per-app UIDs |
| `nftables` | **No** (`CONFIG_NF_TABLES is not set`) | n/a on device | n/a |
| `firewalld` / `ufw` | Not installed | Not implemented (refuses mutation) | No |

On the live handset every UI/WebKit socket-producing process runs as root, so
per-app attribution is **unavailable** and is shown as unsupported, never green.

## Remote-access safety
- `nuxel_firewall/remote.py` reads `sshd -T`, `ss` listeners and established
  sessions before any apply.
- SSH (port 22 on the device) is prepared as `nuxel-ssh-owner` from live sshd
  `AllowUsers` CIDRs; apply refuses input-deny without a prepared SSH allowlist.
- XRDP (13389) and VNC (15900) are OFF by default and only become active when a
  real listener exists; VNC is loopback/SSH-tunnel-only by default.

## Safe apply / rollback
- Dry run renders + validates with no mutation (`services/nuxel-firewall/nuxel_firewall/transaction.py`).
- Apply snapshots first, arms an independent rollback timer, then mutates only
  Nuxel-owned objects (no `nft flush ruleset`, no global `iptables -F`).
- Confirm records last-known-good; timeout/failure/boot-with-pending restores it.

## CLI recovery (serial console)
```text
nuxel-firewall status
nuxel-firewall backend-probe
nuxel-firewall dry-run
nuxel-firewall apply --rollback-after 60
nuxel-firewall confirm
nuxel-firewall rollback
nuxel-firewall evidence
nuxel-firewall self-test
```
State lives under `/var/lib/nuxel/firewall/` (last-known-good, snapshots, audit).

## Known limitations
- nftables unavailable on the S10+ kernel (no nf_tables).
- cgroup-based per-app matching unavailable (no xtables cgroup match; cgroup2
  unified with only `memory pids` controllers).
- Per-app UID matching unavailable because all app processes run as root.
- The `iptables` backend requires installing the `iptables-legacy` binary
  (`dnf install iptables-legacy`) before it can enforce on the device.
- firewalld/UFW adapters are detection-only in this revision.
