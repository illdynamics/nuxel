# Nuxel Security Defaults

> **Nuxel v0.2.2-alpha** — Consolidated "secure by default" policy applied to every
> PWA and native app at install/launch time. Companion to
> [`docs/security-model.md`](security-model.md), which describes the overall
> threat model and layered architecture. This document lists the *prescriptive
> defaults* actually applied by the build group, file by file.

Every Nuxel app starts with *zero* capabilities. A user must explicitly grant a
capability (network, camera, mic, location, notifications) via
`nuxel-permissions`/the portal before the app can use it. These defaults are
enforced by the sandbox launcher (`shell/nuxel-shell/nuxel-sandbox/`), the
per-app nftables firewall, AppArmor profiles, NetworkManager privacy settings,
and the app registry.

---

## 1. NetworkManager — MAC randomization (briq-15)

**File:** `configs/networkmanager/98-nuxel-defaults.conf`
→ installed to `/etc/NetworkManager/conf.d/98-nuxel-defaults.conf`

| Default | Setting |
|---------|---------|
| Per-SSID MAC randomization | `wifi.mac-address-randomization=1` |
| Cloned MAC | `wifi.cloned-mac-address=random` |
| Scan MAC randomization | `wifi.scan-rand-mac-address=yes` |

**Effect:** Upstream scans performed by NM use a random MAC; each connection
randomizes its MAC per SSID. This prevents MAC-based device tracking across
networks. Any connection may opt out with `wifi.cloned-mac-address=permanent`.

## 2. NetworkManager — DNS-over-HTTPS / DNS-over-TLS (briq-15)

**Files:**
- `configs/networkmanager/98-nuxel-dns.conf`
  → `/etc/NetworkManager/conf.d/98-nuxel-dns.conf`
- `configs/networkmanager/resolved-conf.d/nuxel-privacy.conf`
  → `/etc/systemd/resolved.conf.d/nuxel-privacy.conf` (systemd/VM path)
- `configs/networkmanager/nuxel-stubby.yml`
  → `/etc/stubby/stubby.yml` (mustang / OpenRC path)

| Default | Setting |
|---------|---------|
| Prefer local stub resolver | `dns=systemd-resolved` (VM/Fedora); `dns=none` + stubby on mustang/OpenRC |
| IPv4 DNS priority | `ipv4.dns-priority=-1` |
| IPv6 DNS priority | `ipv6.dns-priority=-1` |
| Default upstream hints (IPv4) | `ipv4.dns=1.1.1.1 1.0.0.1` (Cloudflare DoH) |
| Default upstream hints (IPv6) | `ipv6.dns=2606:4700:4700::1111 ... ::1` |
| IPv6 stub | `::1` (systemd-resolved stub at `127.0.0.53`/`::1`) |
| Intended encrypted endpoints | Cloudflare DoH `1.1.1.1`, DoT `1dot1dot1dot1.cloudflare-dns.com` |
| Encrypted transport | `DNSOverTLS=opportunistic` in SHIPPED resolved drop-in; stubby on OpenRC |

**Effect:** A negative DNS priority makes the local encrypted-resolver stub
(which performs DoH/DoT) preferred over any DNS advertised by DHCP, defeating
DNS-based tracking and on-link interception. IPv6 `::1` is explicitly kept as
the resolv.conf stub target.

The encrypted transport is **concrete**, not aspirational:
`resolved-conf.d/nuxel-privacy.conf` pins the encrypted upstreams and enables
`DNSOverTLS=opportunistic`; the mustang/OpenRC path ships `nuxel-stubby.yml`
with the same upstreams (`tls_auth_name 1dot1dot1dot1.cloudflare-dns.com`).

## 3. Per-app network isolation — cgroupv2 + nftables (briq-14)

**Files:**
- `shell/nuxel-shell/nuxel-sandbox/sandbox.c` (Layer 4 cgroup management)
- `shell/nuxel-shell/nuxel-sandbox/nftables.sh` (deterministic app-id mapping)
- `configs/nftables/nuxel-app-firewall.nft` (the `socket cgroupv2 level 2 "app-*"` ruleset)

| Default | Setting |
|---------|---------|
| Per-app cgroup | `/sys/fs/cgroup/nuxel/<app-...>` |
| cgroup name prefix | `app-` (matches nft `socket cgroupv2 level 2 "app-*"`) |
| app-id sanitisation | lowercased, restricted to `[a-z0-9-]`, other chars → `-` |
| `memory.max` | 1 GiB (hard limit) |
| `memory.high` | 512 MiB (soft throttle) |
| cgroup v1 fallback | `cpu`, `memory`, `net_cls` controller files |
| cgroup removal | on process exit |

**Effect:** On app launch the sandbox launcher creates/ensures the per-app
cgroup under `/sys/fs/cgroup/nuxel/`, caps it (1 GiB `memory.max`, 512 MiB
`memory.high`), and moves the child PID into `cgroup.procs`. The nftables
ruleset matches each app's sockets via `socket cgroupv2 level 2 "app-*"`, so
the per-app allow/deny policy applies to the app's actual traffic. Network is
DROPPED by default; only apps granted the `network` capability get a matching
`socket cgroupv2 ... accept` rule. Verify with `nft list ruleset`.

The `--cgroup <app-id>` flag of `nuxel-sandbox` maps deterministically to the
same `app-<id>` string used by the nftables rules; `tools/app-registry-check.sh`
enforces that the registry's `cgroup_name` equals that mapping for every app.

## 4. App registry — single source of app registration (briq-se1)

**Dir:** `configs/nuxel/app-registry/`

| File | Purpose |
|------|---------|
| `app_registry.json` | The registry data (schema_version 1). |
| `app-registry.schema.json` | JSON-Schema validating `app_registry.json`. |
| `README-app-registry.md` | Schema documentation + consumer table. |

`tools/app-registry-check.sh` enforces single-source: every app's `cgroup_name`
MUST equal the deterministic mapping of its `app_id`, and the per-app sandbox
profiles agree with the registry on `cgroup_name` and `network_class`. The
sandbox (`sandbox.c`) and nftables (`nftables.sh`) consume the registry as the
authoritative basis for cgroup naming and network class, keeping them in sync
with the bridge and portal grants.

## 5. AppArmor — enforce mode for every nuxel-* binary (briq-15)

**Directory:** `configs/apparmor.d/`

| Profile | Assets confined |
|---------|-----------------|
| `usr.bin.nuxel-bridge` | bridge D-Bus mediator |
| `usr.bin.nuxel-portal` | portal daemon (consent dialogs) |
| `usr.bin.nuxel-notifications` | notification daemon |
| `usr.bin.nuxel-dialer` | native GTK4 dialer (ModemManager + audio) |
| `usr.bin.nuxel-contacts` | native GTK4 contacts (EDS) |
| `usr.bin.nuxel-messages` | native GTK4 SMS (ModemManager Messaging) |
| `usr.bin.nuxel-settings` | native GTK4 settings (NetworkManager/UPower/ModemManager) |
| `usr.bin.nuxel-permissions` | native GTK4 permissions manager |
| `usr.bin.nuxel-home` | native home launcher |
| `usr.bin.nuxel-sandbox` | the sandbox launcher itself |
| `usr.bin.nuxel-pwa-launcher` | WebKitGTK PWA runner |
| `usr.lib.flatpak` | Flatpak/WPE runtime template |

Each profile uses the `attach_disconnected` flag, includes the standard
abstractions, declares only the minimal file/DBus/network rights the binary
needs, and ends with `deny` rules for raw `/dev`, `/sys`, `/proc/*/mem`, and
`ptrace`.

**Enforce mode** (not complain mode) is enabled by boot/lifecycle units:

- **systemd (VM/Fedora):** `configs/apparmor/systemd/nuxel-apparmor-enforce.service`
- **OpenRC (mustang/Alpine):** `configs/apparmor/openrc/nuxel-apparmor`

Both iterate `configs/apparmor.d/*`, validate each profile with
`apparmor_parser -Q -O enforce`, skip profiles that fail validation with a
warning, and then run `aa-enforce` on the valid ones.

## 6. seccomp + Landlock in the sandbox launch path (briq-15)

**File:** `shell/nuxel-shell/nuxel-sandbox/sandbox.c`

| Sandbox flag | Default | Meaning |
|--------------|---------|---------|
| `NUXXEL_SANDBOX_SANDBOX_SECCOMP` | ON | load the category-specific seccomp BPF allow-list before `exec()` |
| `NUXXEL_SANDBOX_SANDBOX_LANDLOCK` | ON | apply Landlock filesystem restrictions before `exec()` |

The VM bootstrap (`vm/nuxel-vm-bootstrap.sh` → `install_security_hardening`)
installs `/usr/local/bin/nuxel-sandbox-run`, a wrapper that always launches
apps with **both** `--seccomp` and `--landlock` (plus the required `--cgroup
<app-id>`), so every PWA and native app is born with seccomp+Landlock active.

- **seccomp** default-deny allow-list per app category (PWA most restricted;
  native additionally gets socket/GTK4 syscalls; network syscalls only if the
  `network` capability is granted).
- **Landlock** restricts file access to `/usr`, `/etc`, the app's `data_dir`,
  and any explicitly listed RO/RW paths; on ABI ≥ 4, TCP bind/connect is also
  restricted when the app has no network capability.

## 7. Related hardening defaults (context)

These are enforced by sibling build groups but compose with the above:

- **hardened_malloc** preload (`configs/hardened-malloc.conf` +
  `configs/hardened-malloc.service.d/00-nuxel.conf`) — GrapheneOS-style heap
  hardening for every nuxel service/process.
- **dm-verity / AVB / LUKS2 userdata** (mustang image scaffolding) protect
  system and userdata at rest.
- **Minimum kernel 6.12 LTS** with Landlock ABI 4, seccomp, cgroupv2 and
  AppArmor upstream features enabled (Phase 0 kernel bring-up).

---

## 8. Verification

Run on a booted Nuxel system:

```bash
# AppArmor profiles loaded + enforced
sudo aa-status --enforced | grep nuxel
# per-profile parse check (each of the following must print nothing)
for p in /etc/apparmor.d/usr.bin.nuxel-*; do apparmor_parser -Q -O enforce "$p"; done

# NetworkManager privacy defaults active
grep -r "mac-address-randomization" /etc/NetworkManager/conf.d/98-nuxel-defaults.conf
grep -r "dns-priority" /etc/NetworkManager/conf.d/98-nuxel-dns.conf
# DoH/DoT transport actually present (not aspirational)
test -f /etc/systemd/resolved.conf.d/nuxel-privacy.conf || test -f /etc/stubby/stubby.yml

# App registry single-source (briq-se1)
tools/app-registry-check.sh

# Per-app cgroup + nftables socket match (briq-14)
./nuxel-sandbox --cgroup test-app /bin/sleep 5 &   # while running:
ls /sys/fs/cgroup/nuxel/            # expect app-test-app
nft list ruleset | grep cgroup      # expect socket cgroupv2 matches
```
