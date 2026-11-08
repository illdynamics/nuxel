# NUXEL FIREWALL — FULL IMPLEMENTATION / PWNAGE PROMPT

**Mission:** Build a complete, production-grade Nuxel Firewall application and its underlying privileged enforcement service. The user experience should take inspiration from Android AFWall+ (especially its compact per-app network matrix), but the implementation must be Linux-native and must integrate with the actual Nuxel architecture, kernel versions, app registry, networking stack, remote-access services, and recovery paths.

**Primary policy requested by the owner:**

- **Inbound/new unsolicited connections: DENY by default.** Allow only explicit, reviewed service rules.
- **Forwarded/routed traffic: DENY by default.** Hotspot/tethering forwarding must be separately and explicitly configured.
- **Outbound traffic: ALLOW by default.** Every app inherits outbound access on supported network types unless the owner explicitly blocks it. The global outbound default must be configurable, including a strict deny-by-default/allowlist mode.
- **SSH, XRDP and VNC must be accounted for before the firewall is activated.** Do not turn on a ruleset that can strand the owner. Preserve the existing remote-management session and configured trusted access paths. Do not open those ports to the public Internet.
- **Dry-run is mandatory.** The user must be able to see and validate the complete proposed ruleset and its effects before any kernel or firewall-manager state is changed.
- **Persistence:** once deliberately enabled and confirmed, policy must survive reboot and network changes. Pending/unconfirmed applies must never become the boot policy.

This is an implementation task, not a research-only exercise. Inspect the live repository, design the smallest coherent architecture, implement it, integrate it, run the tests, and report only verified functionality. Do not stop after creating a mockup, a configuration schema, or a plan.

---

# 1. Repository-specific audit findings — start here

The supplied repository archive (`nuxel-main (12).zip`, snapshot dated 2026-11-04) already contains substantial firewall infrastructure. Extend and correct it; do not build a competing firewall stack from scratch.

## 1.1 Existing firewall implementation

Relevant files include:

- `tools/s10plus/a33/nuxel-firewall.sh` — existing controller with kernel-mode reporting, policy rendering, `nft -c` checking, snapshots, application, rollback, confirmation, evidence capture, interface configuration, per-app allow/deny commands, VPN kill-switch controls, and an offline mock-nft test mode.
- `configs/nftables/nuxel-firewall-config.json` — current policy document.
- `configs/nftables/nuxel-app-firewall.nft` — current S10+ / Linux 4.14 path using cgroup-v1 `net_cls` class IDs via `meta cgroup`.
- `configs/nftables/nuxel-app-firewall-cgroupv2.nft` — future/newer-kernel cgroup-v2 path.
- `configs/nftables/nuxel-console-guard.nft` — existing console/management guard.
- `configs/nftables/nuxel-vpn-killswitch.nft` — VPN kill-switch rules.
- `configs/nftables/systemd/nuxel-firewall.service` — boot-time service template.
- `shell/nuxel-shell/nuxel-sandbox/nftables.sh` and `shell/nuxel-shell/nuxel-sandbox/sandbox.c` — app cgroup creation and per-app firewall integration.
- `tools/s10plus/a33/security-tests/test-firewall.sh` and `tools/s10plus/a33/security-fixtures/mock-nft` — existing offline firewall test infrastructure.
- `configs/nuxel/app-registry/app_registry.json` — native app/cgroup metadata.
- `pwa/nuxel-common/app-registry.json` — launcher-facing installed-app inventory.
- `pwa/nuxel-apps/settings/index.html`, `settings.js`, `settings-model.js` — existing Settings implementation and `NuxelHost` bridge pattern.
- `configs/nuxel/security/remote-access.json` — authoritative remote-access intent and safety constraints.
- `configs/nuxel/security/ssh/60-nuxel-tri-link.conf` and `62-nuxel-remote-desktop.conf` — SSH and SSH-forwarding policy.
- `services/nuxel-remote-desktop/` — XRDP/VNC services and their configurations.

There is already a Firewall app icon at `assets/nuxel-applications-icon-pack/04-03_firewall.png` and a Quick Settings icon at `assets/nuxel-quicksettings-icon-pack/23-firewall.png`. Reuse the existing Nuxel assets where appropriate.

The app registry currently lists **Firewall manager** as a required app that is not yet in the tree (`briq-05b-firewall-app`). The note says “one authoritative backend (firewalld or UFW), blocklists, hosts editor with atomic writes.” Supersede that concept note with the architecture in this prompt: one authoritative policy model and one selected enforcement owner, with native nftables as the preferred Nuxel implementation and carefully bounded adapters for existing managers.

## 1.2 Existing policy conflicts with the owner’s requested behavior

The current `configs/nftables/nuxel-firewall-config.json` has `input_policy: drop`, `forward_policy: drop`, **and `output_policy: drop`**. The requested initial policy is `input=drop`, `forward=drop`, **`output=accept`**. Per-app outbound exceptions/blocks must then be layered on top of the configurable outbound default.

Do not blindly retain the current “all app egress is denied unless an ACCEPT is inserted” behavior as the default. Preserve explicit pre-existing per-app restrictions during migration, but the new global outbound default and the default for apps without an explicit override must be `allow`.

## 1.3 Critical nftables guard correctness issue — fix before any enable operation

The existing code loads `nuxel-console-guard.nft` in a separate base chain at priority `-200`, while later Nuxel base chains run at `-150` and `-100`. Comments currently suggest that the earlier guard “always wins.” That is not a valid guarantee.

In nftables, an `accept` verdict ends evaluation of the current base chain but the packet can continue into another base chain attached to the same hook at a later priority. A later base chain can still drop it. A `drop` verdict is final. Therefore, an early `accept` in `nuxel_console_guard` does **not** override a later Nuxel `input` chain with `policy drop`, nor does a priority of `-200` by itself guarantee remote management.

Fix the architecture so each allowed SSH/XRDP/VNC packet is accepted by the actual authoritative policy path and is not subsequently dropped by another Nuxel base chain. Where an external firewall manager owns the host policy, use that manager’s supported API/transaction path rather than assuming a separate Nuxel accept chain overrides it. Test the real combined ruleset, including the final verdict path.

## 1.4 Dangerous global ruleset replacement

`configs/nftables/nuxel-app-firewall.nft` currently begins with `flush ruleset`. That command can erase rules owned by unrelated software, including firewalld, container runtimes, VPN managers, and other system components. It also erases separate guard tables and requires special load ordering to reconstruct them.

**Remove the global `flush ruleset` behavior.** Nuxel may replace only rules and objects that it explicitly owns. Use a namespaced Nuxel table/chain/set design and an atomic update of that owned policy. Preserve foreign tables and services. Do not issue `nft flush ruleset`, `iptables -F` across all tables, `ufw reset`, or any equivalent global destructive reset during normal operation or migration.

## 1.5 Existing remote-access facts to preserve and verify live

The supplied `configs/nuxel/security/remote-access.json` describes:

- SSH console on TCP 22, with key-only authentication and source restrictions. The recorded allowed CIDRs include `10.20.30.0/24`, `10.15.19.0/24`, and loopback.
- The USB NCM networking path is marked `BLOCKED_KERNEL_PANIC` on the S10+ Linux 4.14.253 kernel. Do not reactivate, configure, or advertise NCM/USB networking as a usable recovery path merely because old interface names remain in a config.
- The S10+ serial recovery console `/dev/ttyGS0` is a separate, non-IP recovery path. A normal IP firewall cannot filter that serial device. Do not alter it.
- XRDP uses TCP 3389, TLS and PAM, and is configured for trusted LAN/ZeroTier use. The GUI remote-desktop group is OFF by default and is started only by an explicit owner action.
- VNC/wayvnc uses TCP 5900. The supplied config says encryption is `none` and that it has no VNC password authentication. It must never be exposed to the public Internet. Treat it as trusted-LAN/ZeroTier-only, and offer loopback/SSH-tunnel-only mode as the safer option.
- `62-nuxel-remote-desktop.conf` allows local SSH forwarding to `127.0.0.1:5900` and `127.0.0.1:3389`; preserve this carefully.

The supplied SSH `AllowUsers` policy is already a security control. Do not weaken it or replace it with `AllowUsers *`, password authentication, or an unrestricted wildcard rule. Do not change sshd bind addresses or authentication policy as a shortcut for firewall compatibility.

These are repository facts, not permission to assume the live device still has the same IP address or service state. Re-discover the active state at runtime before applying a ruleset.

## 1.6 Current UI and app attribution caveat

The current Settings tabs include Security, Network, Bluetooth and other system panels, but no Firewall panel. Add the new integration without breaking the existing tab framework.

A particularly important implementation caveat: the current `tools/s10plus/a33/nuxel-pwa-host.c` launches PWA apps through the launcher page using `window.appRegistry.launchApp(app_id)`. PWA content is hosted through a shared WebKit host. A cgroup rule attached to that one host process does not automatically distinguish every PWA app shown in the UI. WebKit may also use separate/shared network processes. **Do not claim per-PWA firewall isolation merely because each PWA has an app ID in the registry.** The process that actually opens the socket must be attributable to the correct app.

Build or adapt genuine per-app process/network isolation for network-capable PWA apps, or explicitly mark that feature as unavailable until the isolation is proven. A visible checkbox is not proof of enforcement.

---

# 2. Product definition and user experience

Build a standalone **Nuxel Firewall** application with a Settings entry point and a Quick Settings status/toggle integration. This is a phone-first firewall control center, not a generic desktop firewall configuration editor.

Use AFWall+ as interaction inspiration:

- One compact, scrollable list of installed applications.
- A persistent app icon/name column and network-type columns.
- A checkbox/switch in each app/network intersection.
- Search and filters.
- Column-wide select/clear/invert actions.
- Clear distinction between staged edits and rules currently applied to the kernel.
- Profiles, rule inspection, logs, import/export, and a master firewall state.

AFWall+’s list-and-matrix, per-network app policy, bulk operations, search, profiles, logs, and rule viewer are the useful interaction patterns. Recreate those ideas in Nuxel’s design language. Do not copy AFWall+ source code, branding, logos, screenshots, or exact artwork. The new product is Nuxel Firewall.

## 2.1 Application identity and registration

Create a real app entry, not just an icon or a Settings panel:

- Stable app ID: `org.nuxel.Firewall` (or follow the repository’s canonical ID convention after inspection; choose one ID and use it consistently).
- Add the app to the launcher-facing registry, native app registry if required, app packaging manifests, and any app-tree/registry verification manifests.
- Use the existing Firewall icon asset where it matches the Nuxel app icon rendering rules.
- Provide a dedicated application directory under `pwa/nuxel-apps/firewall/` if built as a PWA, or the correct native application source path if the repository’s actual packaging path requires a native GTK app. Follow existing app conventions rather than creating a second packaging model.
- The app must open on a small phone display, support touch, and remain usable at S10+ resolution and the project’s supported smaller-screen configurations.
- Add a Settings → Security → Firewall entry which opens the actual application/panel and displays a reliable current status. Do not duplicate policy state in Settings.
- Add a Quick Settings Firewall tile using the existing firewall tile icon. It may show status and provide a safe enable/disable action, but all state changes must go through the same daemon/API as the full app.

## 2.2 Main screen layout

The main screen must make the current state obvious at a glance:

1. Header with Nuxel Firewall icon/name and a large shield state: `ACTIVE`, `INACTIVE`, `APPLYING`, `DRY RUN`, `ROLLING BACK`, `ERROR`, or `PARTIALLY ENFORCED`.
2. Backend row: selected backend, backend version, kernel capability status, IPv4/IPv6 state, app-identity enforcement status, and last successful apply time.
3. A short policy summary:
   - Incoming: Deny by default.
   - Forwarded: Deny by default.
   - Outgoing: Allow by default (or the configured selected policy).
4. Primary controls: `Dry run`, `Review changes`, `Apply`, `Confirm`, `Rollback`, and a carefully guarded master enable/disable control. Only render actions that are valid in the current transaction state.
5. Main tab or segmented navigation: `Apps`, `Inbound`, `Rules`, `Networks`, `Profiles`, `Logs`, `Advanced`.
6. Persistent indication of unapplied changes, failed backend status, missing features, and rollback countdown.

Never show a green active shield based merely on saved JSON or a systemd unit being enabled. The app must read back the actual active rules and compare them with the intended policy. If the backend is unavailable, say `NOT ENFORCED` or `UNKNOWN` rather than claiming protection.

## 2.3 The AFWall+-inspired app matrix

This is the core product surface.

Each row contains:

- App icon.
- Friendly app name.
- Short app ID or package/app identifier in details view.
- App category (`Nuxel system`, `Native`, `PWA`, `Flatpak`, `RPM`, `Other`) where known.
- Running/installed state.
- Network identity status (`Verified`, `Shared process`, `No cgroup`, `Unsupported`, `Unknown`).
- Per-network egress toggles.

Use a compact matrix similar in information density to AFWall+, with touch-friendly controls. Column headers must show recognizable icons plus accessible text labels/tooltips. On narrow screens, keep the app-name column visible and permit horizontal scrolling of network columns. Use sticky headers and avoid tiny, difficult-to-tap checkboxes.

Recommended Nuxel columns:

- **LAN** — destinations within the currently connected local subnet(s), not arbitrary private addresses on the Internet.
- **Wi-Fi** — non-LAN egress through the Wi-Fi station interface.
- **Cellular** — only when a real cellular interface is present and verified (for example, `rmnet*` or the live ModemManager-provided device mapping). If the S10+ has no modem data path, show `Unavailable`/disabled, not a working toggle.
- **VPN / Mesh** — egress whose actual route uses an active VPN or ZeroTier interface (for example, verified `tun*`, `wg*`, or `zt*` interfaces). Do not classify a packet as VPN merely because a VPN is configured; inspect the actual route/interface.
- **USB network** — only for an actually available USB network interface; do not mistake `/dev/ttyGS0` serial console for IP networking, and do not enable the known-panicking NCM path.
- **Wired / Other** — Ethernet or other supported physical interface types discovered at runtime.

You may include Bluetooth PAN if the networking stack exposes a real interface and it is verified. Do not show fictional columns for unsupported hardware.

### Network-column semantics

- A checked box means **outbound network traffic is allowed** for that app on that effective network category.
- An unchecked box means **outbound network traffic is blocked** for that app on that category.
- Show inherited defaults distinctly from explicit per-app overrides (for example, a checked-but-inherited indicator vs a checked explicit override). The user must be able to understand why an app is currently allowed.
- The `LAN` classification is destination-based: use the connected network’s actual route prefixes/subnets and a well-defined IPv4/IPv6 local-network classification. Do not equate “Wi-Fi” with “LAN”; Internet traffic via Wi-Fi and traffic to local peers are different policy dimensions.
- If a packet is destined for a connected LAN subnet, the LAN control governs it. The Wi-Fi control governs non-LAN egress over Wi-Fi. Document precedence and test it.
- VPN policy uses the actual egress route. If the VPN tunnel is down, the VPN column is not silently converted to Wi-Fi or cellular allow.
- Hotspot clients are **forwarded traffic**, not local app egress. Put hotspot/tethering client forwarding under a separate Forwarding panel and default it to blocked.

### Global outbound modes

Provide a simple global setting:

- `Allow outgoing by default` — initial/default mode requested by the owner.
- `Block outgoing by default` — strict allowlist mode.

The app matrix must work in both modes:

- In allow-by-default mode, each new app inherits `Allow` for all supported outbound network categories until explicitly blocked.
- In block-by-default mode, each new app inherits `Block` until explicitly allowed.
- Existing explicit app restrictions must survive migration unless the owner deliberately changes them. Do not silently turn an explicitly isolated app into an unrestricted app merely because the new global default changes.
- Existing explicit public/allowed app policies remain allowed.
- Apps without an explicit old override inherit the new global default (`Allow`).
- Provide clear `Reset app to inherited default`, `Allow all networks`, and `Block all networks` row actions.
- A global network-type default may optionally be more restrictive than the overall outbound default, but make the effective rule visible.

## 2.4 Search, filter, sorting and bulk operations

Implement:

- Search by friendly name, stable app ID, executable, desktop ID, Flatpak application ID, and package identifier where available.
- Filters: All, Allowed, Blocked, Mixed, New, System, User, PWA, Native, Flatpak, Running, Unsupported identity.
- Sort by name, recently installed, recently used/running, network access, or app category.
- Select all / clear all / invert one network column.
- Bulk allow/block selected apps for one network category or all categories.
- Bulk actions must show an explicit count and a confirmation summary before applying.
- When a newly installed app appears, display a subtle `NEW` state and apply the configured global inherited default. Never auto-add it to a permanent allow exception outside the owner’s selected default policy.

## 2.5 Inbound services and trusted remote access

Inbound access is not controlled by the app egress matrix. Create an explicit `Inbound`/`Services` surface that lists system listeners and narrow service rules.

Show at least:

- SSH console (port discovered from effective sshd configuration and actual listening socket; repository default/current expected port 22).
- Optional SSH alternate port 2022 only if it is truly configured/listening.
- XRDP (TCP 3389 when service and listener are enabled).
- VNC / wayvnc (TCP 5900 when service and listener are enabled).
- Other active listening services discovered via systemd/socket inspection, each shown as a separate review item.

Each rule must display:

- Protocol and port.
- Listening/bind addresses.
- Inbound interface(s).
- Allowed source IP(s)/CIDR(s).
- Service active/inactive state.
- Whether the rule is currently enforced, prepared but inactive, or blocked by a capability gap.
- Security note where relevant (XRDP TLS/PAM; VNC unencrypted/no VNC password auth in the current config).

Do not automatically expose all detected listening ports. A listener is not permission to expose it.

---

# 3. Firewall policy model and default behavior

Create one canonical, versioned, validated policy model. The UI, daemon, backend compiler, CLI, boot loader, profile manager, and audit logs must all consume the same schema.

A conceptual policy model:

```json
{
  "schema_version": 1,
  "enabled": false,
  "backend": "auto",
  "defaults": {
    "input": "deny",
    "forward": "deny",
    "output": "allow",
    "ipv4": true,
    "ipv6": true
  },
  "app_defaults": {
    "outbound": "inherit_global",
    "new_app_policy": "inherit"
  },
  "services": {},
  "apps": {},
  "networks": {},
  "logging": {},
  "safety": {},
  "profiles": {}
}
```

The example is explanatory. Inspect existing config layout and use the canonical Nuxel paths and schema naming conventions. Do not duplicate or maintain conflicting policy JSON files.

## 3.1 Direction policy

Initial policy:

| Direction | Default | Meaning |
|---|---|---|
| INPUT | `drop` | Unsolicited inbound connections denied unless a specific service rule allows them. Established/related replies and essential networking control traffic are handled narrowly. |
| FORWARD | `drop` | Device does not route/tether traffic unless an explicit forwarding profile enables it. |
| OUTPUT | `accept` | Outbound traffic allowed by default. App-level and interface-level explicit deny rules can block it. |

These are separate settings, not one vague “default deny” switch. UI language must state the direction affected.

### INPUT

- Default drop for new inbound traffic.
- Permit established/related reply traffic.
- Permit loopback.
- Permit only narrowly required IPv4/IPv6 control traffic (DHCP client/server exchange as appropriate, IPv6 neighbor discovery/router advertisement/solicitation, path-MTU and destination-unreachable ICMP types needed for normal network operation).
- Do not blanket-allow all ICMP or all DHCP on every interface if it is not required.
- SSH/XRDP/VNC exceptions must be explicit and source/interface-restricted.
- No open inbound port by default beyond the verified remote-management allowlist.

### FORWARD

- Default drop.
- A future Wi-Fi hotspot, USB tether, or Bluetooth PAN forwarding mode must use a separate explicit wizard and explain routing/NAT/conntrack effects.
- The forwarding UI must separately control ingress interface, egress interface, client subnet, protocols, DNS/DHCP support, and any NAT rule.
- Never turn on routing merely because NetworkManager reports a hotspot profile.

### OUTPUT

- Initial default allow for all outbound app/system traffic, as requested.
- Per-app egress controls generate explicit deny/allow overrides based on the global outbound default.
- If the owner switches to global deny, only explicitly allowed apps/system services and essential network-control paths may egress.
- A per-app block must block new and existing flows for that app and must not be bypassed by an early generic `ct state established,related accept` rule. Rule ordering must ensure the explicit app deny is evaluated before a generic established-flow accept.
- Conversely, when input policy is deny, the firewall must not break valid replies to connections initiated from the device.
- Do not insert a universal DNS/ICMP/DHCP accept ahead of per-app deny rules in a way that lets a blocked app still communicate. System resolver and DHCP services must be identified and treated separately from app-originated packets.

## 3.2 IPv4 and IPv6 parity

- Apply the selected policy to both IPv4 and IPv6 by default.
- Do not accidentally secure IPv4 while leaving IPv6 wide open, or vice versa.
- Keep IPv6 neighbor discovery, router discovery, DHCPv6 where used, and path-MTU behavior functional.
- Display IPv4 and IPv6 enforcement status independently.
- If the selected backend cannot enforce one family, show `PARTIALLY ENFORCED` and refuse to call the firewall fully active unless the owner explicitly accepts a clearly described reduced policy.
- Include link-local, loopback, multicast, broadcast and ULA handling in tests.

## 3.3 Stateful connection behavior

- Use conntrack/stateful filtering where supported.
- A denied app’s existing flow must be terminated from the policy perspective; do not let an `ESTABLISHED` exception bypass a newly applied app deny.
- On a global policy update, preserve established management traffic only as needed for the safe-apply transaction; do not create a permanent broad exception from that requirement.
- New inbound connections remain denied unless a specific allow rule matches.

## 3.4 System services and unclassified traffic

- Explicitly inventory system daemons that need outbound network access (NetworkManager, ModemManager if present, the active DNS resolver, NTP/timesync, VPN daemon, update service, and the firewall’s own local control socket).
- Assign system daemons their own systemd service/cgroup or verified UID identity where possible.
- Do not treat all unclassified/root traffic as a single “trusted system” group without documenting it.
- Root can generally alter host firewall state. State the threat boundary honestly; this app is not a defense against a malicious process already running as root.
- Do not silently bypass the policy for all traffic with `meta cgroup 0 accept` or equivalent. If an unavoidable class of traffic is not classifiable, display it as an explicit coverage gap and measure it.

---

# 4. Backend architecture — one policy owner, no conflicting managers

Linux Netfilter is the kernel packet-filtering subsystem. `nftables` and `iptables` are rule-management interfaces to it. UFW and firewalld are higher-level management frameworks/frontends; they must not be treated as independent kernel firewall engines that can be stacked without coordination.

Implement a backend adapter architecture behind one Nuxel policy daemon/API. Detect and select exactly one authoritative owner for each host policy. Never have Nuxel, UFW, firewalld, and a standalone nftables service independently rewrite the same policy at boot.

## 4.1 Preferred Nuxel backend: native nftables

This is the preferred backend because the repository already has a substantial nftables implementation and needs granular cgroup/per-app rules.

Requirements:

- Use one Nuxel-owned namespace/table (for example `inet nuxel_firewall`) with explicit ownership comments/metadata.
- Do not touch foreign tables.
- Prefer a single authoritative Nuxel base chain per hook where possible, with service exceptions and app policy integrated into the same policy path. Avoid separate high-priority “accept guard” chains that are later defeated by another base-chain drop.
- Reconcile all existing Nuxel tables/chains from `nuxel-app-firewall.nft`, `nuxel_ifaces`, `nuxel_console_guard`, VPN-killswitch and sandbox helper. Remove obsolete duplicate base chains after a verified migration.
- Use nftables sets/maps for app class IDs, interface groups, trusted source CIDRs, ports and dynamic LAN prefixes to avoid thousands of individual rules.
- Use rule counters for observability.
- Use atomic `nft -f` batch updates only on Nuxel-owned objects. Build a complete batch, syntax-check it, then apply it transactionally.
- Use `nft -a list ruleset` / `nft list table inet nuxel_firewall` to read back actual rule state and handles.
- If an nft command fails, restore only Nuxel-owned prior state and leave all foreign tables untouched.
- Never claim a feature is enabled if its rules cannot be found and verified in the live ruleset.

### Kernel-aware per-app nftables matching

The repository targets at least two kernel postures:

- Samsung S10+ / `beyond2lte`: Linux `4.14.253`, where the existing implementation uses cgroup-v1 `net_cls` class IDs and `meta cgroup` matching.
- Newer/future kernels such as 6.12, where the repository has a cgroup-v2 socket matching ruleset (`socket cgroupv2 level 2 ...`).

Do not select capability solely by parsing `uname -r` or assuming every kernel has the same backports/modules/userspace support. Probe the real device:

- Kernel release and configuration where available.
- cgroup v1/v2 mount layout.
- Whether `net_cls` exists and is writable on the target kernel.
- Whether nftables userspace and kernel accept the exact `meta cgroup` or `socket cgroupv2` expression.
- Whether the Nuxel app launcher actually attaches the socket-producing process to the intended cgroup before it opens a network socket.
- Whether the packet counters for the intended app rule actually increment under live test traffic.

Use the existing `nuxel-firewall.sh probe` as a starting point, but strengthen it. A syntax check alone is not proof of app attribution. A successful cgroup write alone is not proof of firewall enforcement.

The S10+ `net_cls` code and class IDs must be reconciled with `nuxel-permd.py` / sandbox `_classid_for()` and the app registry. There must be one deterministic app ID → kernel network identity mapping. Detect collisions and refuse ambiguous class IDs.

### Critical cgroup race

Ensure a child process is attached to its app cgroup **before** it can execute arbitrary app code or open sockets. Use a fork/exec gate, parent-child synchronization pipe, or equivalent: child waits; parent assigns PID/cgroup and verifies readback; only then may the child `exec` the application. Do not spawn an app, allow it to run briefly outside its cgroup, and attach it after the fact.

### PWA process attribution is a required work item

The current shared WebKit host cannot be assumed to provide per-PWA cgroup isolation. Inspect the actual WebKit process model on the device and determine which process creates the sockets.

Implement a real isolation strategy for each network-capable PWA, such as:

- dedicated per-app host + WebKit process/network process pool, with the complete socket-producing process tree assigned to that app’s cgroup; or
- a per-app network proxy/process design where the PWA cannot make direct external sockets and the proxy has independently verifiable per-app identity and enforcement.

Whichever method is chosen, prove it with two PWA apps using the same destination: allow one, deny the other, and demonstrate at the kernel layer that only the allowed app can communicate. Include a bypass attempt using direct IP, alternate port, IPv6, UDP and a second WebKit/network process. If this cannot be fully solved for every PWA type in this implementation, disable those controls for that app and display `Per-app attribution unavailable`; do not fake success.

## 4.2 firewalld adapter

If firewalld is already active and owns the host firewall:

- Use firewalld’s supported D-Bus API as the primary integration surface. `firewall-cmd` may be used for diagnostics and controlled operations, but avoid parsing unstable human-formatted output as the only source of truth.
- Use zones, services, source/interface bindings and policies for inbound/forwarding service controls.
- Understand runtime versus permanent configuration. Show both states; a runtime allow is not automatically persistent.
- Use the supported firewalld transaction/update semantics and save/rollback the exact prior Nuxel-managed firewalld objects.
- Do not write directly into firewalld-owned nftables tables or change `NftablesTableOwner` to bypass ownership.
- Do not assume an independent Nuxel nftables base chain can override a later firewalld chain.
- Do not report per-app controls as working unless a separately tested and supported cgroup/UID enforcement mechanism has been integrated without conflicting with firewalld. Otherwise show the global/service controls as supported and per-app filtering as unavailable under this backend.
- Do not stop/disable firewalld automatically. Switching backend requires a migration preview and explicit owner confirmation.

## 4.3 UFW adapter

If UFW is already active and is the authoritative manager:

- Use UFW’s supported command interface and rule numbering for its managed rules.
- Use `ufw --dry-run` as one part of preview, but still perform Nuxel’s own policy validation and remote-access safety analysis.
- Support default incoming deny, routed deny, outgoing allow, per-interface service rules, and source-CIDR restrictions.
- Snapshot UFW configuration before persistent changes; distinguish runtime and persistent state.
- Do not use `ufw reset` as a normal configuration tool.
- Do not enable UFW before inserting and verifying the management allow rules. UFW enable/reload behavior may change chains and interrupt existing connections; the safe-apply transaction must account for that.
- UFW application profiles are service/port descriptions; they are not a general per-process app-network identity mechanism. Do not pretend that an UFW application profile provides AFWall+-style per-installed-app egress control.
- If the owner wants granular per-app matrix support and UFW cannot provide it, propose a controlled migration to Nuxel native nftables, with export/backup and rollback. Never silently replace UFW.

## 4.4 iptables adapter / compatibility

Support iptables only where it is genuinely required and detected:

- Distinguish `iptables-legacy` from `iptables-nft` (`iptables -V` and alternatives/backend introspection).
- Use `iptables-save` / `iptables-restore` and `ip6tables-save` / `ip6tables-restore` for snapshot/restore, but only manage Nuxel-owned chains.
- For per-app filtering, require a verified `xt_cgroup`/cgroup match or unique per-app UID/owner match. A single shared UID for all Nuxel apps cannot provide per-app attribution.
- Verify both IPv4 and IPv6 (`ip6tables`) coverage.
- Do not apply iptables-legacy and native nftables rules to the same intended policy simultaneously without a tested explicit architecture.
- Show unsupported capabilities honestly.

## 4.5 Backend discovery and conflicts

At startup and before every apply, inspect read-only state:

- `systemctl is-active firewalld`, `systemctl is-enabled firewalld`, D-Bus availability.
- UFW installation/status/configuration.
- `nft --version`, `nft list ruleset`, presence of existing Nuxel and foreign tables.
- `iptables -V`, `ip6tables -V`, `iptables-save`, `ip6tables-save` where available.
- Running container/network/VPN tools that may own firewall chains.
- Existing network configuration, active NetworkManager connections and VPN interfaces.

Selection policy:

1. If a single supported manager is already active, use its adapter or ask for a safe explicit migration. Do not run a second manager behind it.
2. If both UFW and firewalld are active, or state is ambiguous, refuse mutation and show a conflict report.
3. If native nftables is selected, ensure there is no active competing owner that could later discard or override Nuxel policy. The user must explicitly choose the authoritative manager.
4. Never install, enable, disable, mask or unmask firewall managers automatically as a side effect of opening the application.
5. Never claim `ACTIVE` where only a policy file exists or a backend command is missing.

The app must have a `Backend diagnostics` screen that shows the exact detected backend, version, active service, ruleset owner, supported directions/families, app attribution support, and unsupported features.

---

# 5. Remote-access protection and safe activation — highest priority

This section is a hard gate. A firewall that locks the owner out is a failed implementation.

## 5.1 Discovery before policy generation

Before rendering or applying any rules, collect live facts:

- Active SSH daemon/service units and socket activation state.
- Actual TCP listening sockets, addresses, and ports (`ss -lntp` or a structured netlink equivalent).
- Effective sshd configuration (`sshd -T` with appropriate context and/or robust parsing of included configuration) including authentication, `AllowUsers`, forwarding policy, and port/listen settings.
- Current established SSH sessions and their peer IP, local IP, interface/route, and destination port. Discover from socket/conntrack/process information; do not assume the manager’s own environment inherited `SSH_CONNECTION`.
- Current NetworkManager active connections and addresses/routes.
- Actual ZeroTier interface/network status if installed and active; identify the real interface and authorized peer/network range from live configuration.
- XRDP service/socket state, actual listener, `xrdp.ini`, TLS certificate/key presence, and remote-access policy.
- VNC/wayvnc service state, actual listener, configuration, authentication/encryption state, and Wayland session status.
- Whether USB gadget network interfaces actually exist. Treat the known S10+ NCM path as unavailable unless fresh safe hardware evidence proves otherwise.

Do not edit sshd, XRDP, VNC or NetworkManager settings just to make the firewall work.

## 5.2 SSH allowlist

Create the SSH allow rule **before** any new drop policy is activated.

- Discover the effective SSH port(s); TCP 22 is expected, while 2022 is allowed only if actually configured/listening or explicitly enabled in Nuxel policy.
- Apply to the correct real ingress interface(s), not `iifname "*"` without source restrictions.
- Mirror the existing SSH authorized source CIDRs from the active `AllowUsers` and Nuxel remote-access policy. At the time of the supplied repository snapshot, these include `10.20.30.0/24`, `10.15.19.0/24`, and loopback; verify the live policy and live interface state.
- The firewall CIDR policy must never be broader than the SSH daemon's actual authentication/source policy.
- Preserve current established SSH sessions and ensure a **new** connection from an authorized management peer can be established after applying the rules.
- If the current administrator’s peer IP is outside the configured allowlist, do not silently open the port to the world. Offer a precise, temporary `/32` or `/128` session exception for the current peer, display it clearly, and require explicit confirmation. The exception must be removed or converted to a deliberately approved persistent management source after the session is independently verified.
- Key-only SSH and sshd’s restrictions remain active. Never enable password authentication, unrestricted root login, or wildcard source access.

## 5.3 XRDP allowlist

Prepare an XRDP service policy entry before enabling the firewall:

- TCP 3389 only when the XRDP service is explicitly enabled and actually listening.
- Restrict source addresses to trusted owner LAN and verified ZeroTier/mesh peers, not `0.0.0.0/0` or all public interfaces.
- Only apply on active/approved ingress interfaces.
- Require TLS/PAM configuration to pass its own validation; do not infer it merely from the port number.
- Keep the service OFF by default as the current remote-access config specifies.
- The Remote Desktop start action must call the firewall manager first. It may start XRDP only after the corresponding allow rule is previewed, verified and applied. On stop, it may remove the transient allow rule after existing sessions are closed or the owner confirms.

## 5.4 VNC / wayvnc allowlist

Prepare the VNC policy entry before enabling the firewall:

- TCP 5900 only when wayvnc is explicitly started and actually listening.
- The existing configuration states that VNC has no encryption and no VNC password authentication. Show a visible warning in the UI.
- Never expose 5900 to the public Internet, cellular interface, or an untrusted/public Wi-Fi network.
- Default safe mode should prefer loopback-only plus the existing SSH local-forwarding route (`127.0.0.1:5900` through the fixed SSH `PermitOpen` rule).
- If the owner chooses direct trusted-LAN/ZeroTier VNC, allow only verified trusted source subnets and explicitly show that traffic is unencrypted/unauthenticated at the VNC protocol layer.
- The VNC service must remain off by default.
- Do not allow 5900 merely because the port appears in a configuration file; verify that the service is active and the listener matches the intended bind address.

## 5.5 Remote access must be a first-class firewall concept

Create named inbound service policies:

- `nuxel-ssh-owner` — key-only SSH, exact allowed CIDRs, active management interface(s), dynamic listener port.
- `nuxel-xrdp-owner-lan` — TCP 3389, trusted LAN/verified mesh only, inactive until XRDP is started.
- `nuxel-vnc-owner-lan` — TCP 5900, loopback/SSH tunnel by default; optional trusted LAN/mesh direct access with warning.

These profiles must be visible and editable in the firewall app. They are not broad permanent port openings.

## 5.6 Console recovery invariant

- `/dev/ttyGS0` serial console must remain untouched.
- Do not alter bootloader, partition, flashing, kernel, USB configfs, or modem state as part of this firewall task.
- Keep an independently documented recovery method available (serial console and existing verified recovery instructions).
- Do not claim USB networking as a fallback when its live status is `BLOCKED_KERNEL_PANIC`.
- The app must show the last-known-good policy and have a CLI rollback path usable from the serial recovery shell.

---

# 6. Dry-run, transactional apply, confirmation and rollback

A dry-run is mandatory and must be meaningful.

## 6.1 Dry-run requirements

The `Dry run` action must:

1. Read the current active policy, backend state, services, interfaces, addresses, routes and actual listening sockets.
2. Validate the policy JSON/schema and reject unknown keys, invalid protocols, invalid CIDRs, invalid ports, duplicate app IDs, invalid network interface references, and ambiguous identities.
3. Render the exact intended backend rules/configuration to a temporary file or backend plan.
4. Run backend syntax checks (`nft -c -f`, UFW dry-run, or adapter-specific validation) without changing kernel state.
5. Detect active backend conflicts and unsupported kernel features.
6. Compare the desired state with the current live state and produce a human-readable diff.
7. Display every management allow rule that will be installed, including interface, port, source CIDR and owning service.
8. Detect whether any current inbound management session would be interrupted.
9. Detect whether a firewall-owned table or manager would overwrite another component’s rules.
10. Produce a structured report that the UI can render and export.

Dry-run must not:

- Change live firewall rules.
- Enable/disable/reload firewalld or UFW.
- Restart SSH/XRDP/VNC/NetworkManager/VPN services.
- Install packages.
- Change persistent configuration.
- Start a listener or open a port.

Use temporary state only under `/run/nuxel/...` or a dedicated test directory. Make it impossible for a dry-run path to accidentally execute the mutating backend call.

Important: `nft -c` and `ufw --dry-run` validate generated syntax/plan; they do not prove end-to-end network reachability or that the actual packet will traverse the expected cgroup identity. The UI/report must state that limitation.

## 6.2 Pre-apply safety gate

Block Apply unless all of these are true:

- A supported backend is selected and healthy.
- The exact current SSH allowlist has been resolved.
- The existing remote session has been recorded if the action is remote-initiated.
- The desired SSH service rule appears in the final authoritative input chain or active manager policy.
- XRDP/VNC profiles are correctly prepared and inactive unless their services are actually enabled.
- IPv4 and IPv6 behavior is known.
- The Nuxel ruleset does not use a global `flush ruleset`/global iptables flush.
- Backend syntax/structural validation passes.
- A complete pre-apply snapshot can be stored.
- The independent serial recovery path is not modified.
- The rollback service/timer is ready before the first mutating operation.

If a gate fails, refuse activation and show the precise reason. Do not silently skip the failed check.

## 6.3 First enable and every risky policy update

For first activation and any policy update that could affect inbound or active management:

1. Build and display the complete diff.
2. Require an explicit owner action such as `Apply with 60-second rollback`.
3. Persist a signed/hashed transaction record and snapshot of the exact Nuxel-owned prior policy. For firewalld/UFW adapters, snapshot only the Nuxel-managed configuration plus any manager state that the adapter must mutate.
4. Arm an independent systemd-managed rollback timer **before** changing the live policy. Do not rely only on a background `sleep` process owned by the UI/daemon.
5. Apply the new rules atomically (or through the backend’s supported transactional mechanism).
6. Read back the actual live rule state.
7. Verify management service rules in the final policy path, not only the existence of a separate guard table.
8. Verify current SSH connection remains established and that the SSH listener/route is still available.
9. Report the new state as `UNCONFIRMED — rollback in N seconds`.
10. Require an explicit `Keep changes`/`Confirm` action. The confirmation screen must warn that the user should test a second fresh SSH connection or another trusted management connection before keeping the policy.
11. On confirmation, mark the new state as last-known-good and disarm rollback.
12. On timeout, backend error, daemon crash, missing guard, failed health check, or reboot while pending, restore the previous confirmed policy.

Use a default first-apply confirmation window of at least 60 seconds; make it configurable up to a sensible maximum. The countdown must be visible.

## 6.4 Rollback implementation

- Use a dedicated systemd rollback service/timer or equivalent robust system mechanism, independent from the PWA UI and firewall daemon lifetime.
- Store `pending`, `last_known_good`, snapshot path, backend, policy hash, transaction ID, timestamp and rollback deadline in root-owned state under `/var/lib/nuxel/firewall/` with strict permissions.
- At boot, detect an unconfirmed pending transaction and restore the last-known-good policy before enabling the pending policy.
- Never restore a global foreign ruleset when only Nuxel-managed objects changed.
- Verify rollback succeeded by querying the live backend.
- If rollback cannot be verified, set state to `RECOVERY REQUIRED`, preserve serial access, display exact recovery commands, and do not claim the firewall is active/healthy.
- Maintain a CLI command that can restore last-known-good policy from the serial console without needing the GUI.

## 6.5 No global flushes

This is non-negotiable:

- No `nft flush ruleset`.
- No `iptables -F` across all chains/tables.
- No blind `ufw reset`.
- No firewalld stop/restart used as a shortcut.
- No removal of foreign VPN/container/NetworkManager rules.

A transaction must be scoped to the selected backend and its explicitly Nuxel-owned objects.

---

# 7. Application network identity and app registry integration

AFWall+-style per-app controls only work if the kernel can attribute network packets to the correct installed app.

## 7.1 One canonical installed-app inventory

Inspect and reconcile:

- `pwa/nuxel-common/app-registry.json` (launcher-facing app IDs and PWA/native metadata).
- `configs/nuxel/app-registry/app_registry.json` (native executable, cgroup, class ID, capabilities, data directories).
- Installed Flatpak/RPM/PWA runtime inventory.
- Sandbox profile directory.

Do not create a fourth independent installed-app list. Make a canonical normalized inventory service/API that merges the available sources by stable app ID and records provenance, install source, executable/process entry point, cgroup identity and network enforcement capability.

Missing or conflicting app records must be visible and repaired through the registry flow, not guessed by display name.

## 7.2 Native apps

- Every app launched through `nuxel-sandbox` must receive its app cgroup/network class before execution.
- Assign a unique network identity (cgroup classid or cgroup-v2 path) with deterministic collision detection.
- Verify child processes inherit the expected cgroup unless an explicitly managed helper/service identity is created.
- If an app starts through systemd, use a dedicated systemd unit/scope or another verified mechanism to attach the complete app process tree.
- Do not put unrelated apps in one cgroup.
- Do not use an app ID string in nftables expressions without a stable sanitization/identity mapping and collision check.

## 7.3 Flatpak apps

- Discover Flatpaks from the installed Flatpak app list and desktop entries.
- Determine the actual process/cgroup/UID that generates outbound sockets.
- If Flatpak shares a network process or helper that cannot be attributed to one application, show the limitation; do not claim per-app control.
- Do not weaken Flatpak sandboxing or remove its network namespace restrictions to make firewall controls appear to work.

## 7.4 PWA apps

- Build genuine per-app network attribution as specified in §4.1.
- Test PWA-to-network traffic at the actual socket-producing process, including WebKit’s NetworkProcess and subprocesses.
- A PWA’s app ID or iframe origin is not sufficient kernel identity.
- For app-specific rules to be marked `Verified`, deny one PWA and allow another while proving at the kernel level that the deny works even for existing connections and alternate protocols.

## 7.5 System and privileged services

- List system daemons separately from user apps.
- Give them stable identities or service policies and show them in `System services`/`Advanced`.
- The firewall manager daemon must not be treated as an ordinary untrusted PWA app.
- No app row should imply that a root service is filtered by a non-root cgroup rule when it is not.

## 7.6 Migration of existing network classes

- Preserve prior explicit blocks (`isolated`, `deny`, `network_policy.default=deny`, or equivalent) as explicit app-level denies unless the owner changes them.
- Preserve prior explicit allow policies as explicit allows.
- Apps with no explicit historical override inherit the new global default (`Allow outbound`).
- Show a migration summary: number of apps preserved as denied, preserved as allowed, newly inheriting allow, and not enforceable due to identity limitations.
- Do not bulk-change unknown apps to denied or allowed without making the resulting set visible to the owner.
- Reconcile class IDs with `nuxel-permd.py` and `sandbox.c`; do not maintain a separate inconsistent class ID formula.

---

# 8. Network discovery, interfaces and categories

Use NetworkManager D-Bus/API and kernel route/address data to build the live network model. Do not hardcode `wlan0` as the only Wi-Fi interface or infer trust from a name alone.

For every interface, record:

- Interface name and ifindex.
- Type/technology (Wi-Fi, Ethernet, cellular, VPN, WireGuard, ZeroTier, USB gadget, Bluetooth PAN, loopback, unknown).
- Active/connected state.
- NetworkManager connection UUID/profile and zone/trust label if available.
- IPv4/IPv6 addresses and connected routes.
- Gateway and DNS configuration (where available).
- Default-route status and route metrics.
- Whether it is currently a trusted management interface.

### Trust categories

- `Trusted LAN`: explicitly approved local network or owner mesh; do not equate every RFC1918 address globally with trusted.
- `Untrusted Wi-Fi`: public/unknown Wi-Fi, default untrusted unless owner assigns a profile.
- `Cellular`: mobile WAN.
- `VPN/Mesh`: active verified tunnel or ZeroTier interface.
- `USB network`: active, verified IP interface only; never infer from USB serial.
- `Wired`: physical Ethernet.
- `Loopback`: always local.

Support policy profiles per network, but network classification must reflect the actual route used by each packet.

### Network switching

- Subscribe to NetworkManager changes, route/address changes and VPN state transitions.
- Recompute dynamic subnet sets and service interface bindings on connection changes.
- Reapply only Nuxel-managed policy objects atomically.
- Do not reset the whole firewall on a Wi-Fi roam or VPN reconnect.
- Do not allow a trusted LAN rule to silently apply to a different public Wi-Fi network simply because it uses the same interface name.
- If the current management interface changes, keep the current session safe and re-evaluate before deleting old allow rules.

### VPN kill switch

Retain and strengthen the existing VPN kill switch:

- Option to force selected apps or all app traffic through a chosen VPN interface.
- If the VPN is down, those selected apps must not fall back to ordinary Wi-Fi/cellular.
- The VPN daemon itself needs a narrowly scoped exception to reach its configured endpoint on the underlying physical interface so the tunnel can establish.
- Do not let a VPN kill switch accidentally block SSH/remote desktop management unless the owner explicitly requests that behavior and confirms the recovery route.
- Display `Kill switch armed` separately from `VPN connected`; these are not the same state.
- Verify route and live interface, not just a boolean config flag.

---

# 9. Rules manager

Provide a rules editor for inbound/outbound/forward/service rules, with safe defaults and validation.

Each rule should have:

- Stable rule ID.
- Human-readable name and description.
- Enabled/disabled state.
- Direction: input/output/forward.
- Action: allow/drop/reject (make drop vs reject difference clear; default deny should use drop unless the owner chooses otherwise).
- Protocol: TCP, UDP, ICMP, ICMPv6, SCTP where supported, or any.
- Source and destination address/CIDR.
- Source and destination port/range.
- Interface or network category.
- App/cgroup/UID identity if supported.
- Creation/update timestamp and origin (`user`, `Nuxel default`, `remote-access profile`, `migration`).
- Counter/logging setting.

Requirements:

- More-specific rules must be compiled before broader rules where the selected backend is order-sensitive.
- Display the effective order and effective verdict.
- Prevent contradictory duplicate rules or explain which one wins.
- Validate IPv4 and IPv6 input independently.
- Reject unsafe wildcard exposure for SSH/RDP/VNC unless the owner enters an explicit advanced override with a risk warning.
- Never allow a malformed rule to partially apply.
- Support import/export with schema version and validation; no arbitrary shell scripts from imported files.
- A user rule must never overwrite a system safety invariant silently.

## 9.1 Blocklists and domain/host blocking

The existing briq concept mentions blocklists and a hosts editor. Include a controlled implementation:

- Support curated IP/CIDR blocklists through named nftables sets or corresponding backend mechanisms.
- Store source URL/name, version, last update, checksum, item count, and update time.
- Download/update only through an explicit safe update path; validate data, size limits and CIDR syntax before atomic activation.
- Never insert arbitrary shell content from lists.
- Support a local managed hosts-blocklist editor with atomic writes, backup, validation and rollback.
- Clearly explain that hosts/DNS filtering only covers clients using the system resolver. Apps using DoH/DoT, hard-coded IPs or alternate resolvers may bypass a hosts-only blocklist. Do not advertise it as universal domain blocking.
- Domain filtering must not be represented as application-level firewall coverage unless it is enforced for all relevant resolver paths.

---

# 10. Logs, counters and monitoring

Provide a useful but bounded monitoring system.

- Show blocked connection attempts with app/service identity where verified, direction, interface, protocol, source/destination IP and port, timestamp, and matching rule ID.
- Show counts per app, per rule and per network type.
- Use kernel rule counters and rate-limited logging.
- Do not log every allowed packet by default.
- Bound log volume and retention; avoid filling phone storage.
- Provide filters by app, protocol, destination, time range, direction and action.
- Add optional blocked-connection notifications, configurable globally and per app.
- Allow copy/export of filtered logs using a privacy-aware export format.
- Avoid logging full URLs, page contents, TLS payloads, credentials, or arbitrary packet payloads.
- Explain that a network-layer firewall normally sees IPs/ports/protocols, not HTTPS URL paths.
- If app identity is unknown, log as `Unclassified` rather than guessing.
- Provide an `Active rules`/`Kernel view` screen that displays the actual live backend rules, not just the intended JSON.

---

# 11. Profiles and backups

Implement named profiles with the same robust user experience AFWall+ offers, while using Nuxel’s policy model.

Suggested built-in profiles:

- `Default` — inbound deny, forward deny, outbound allow by default (owner’s requested default).
- `Strict outbound` — inbound deny, forward deny, outbound deny by default with explicit allowlist.
- `Trusted Wi-Fi` — normal outbound policy with user-selected LAN/service options.
- `Public Wi-Fi` — conservative inbound, no LAN service exposure, outbound per-app policy retained.
- `VPN only` — selected/all apps egress only over verified VPN, with explicit VPN endpoint exception.
- `Offline` — block all nonessential egress; retain only required local/system management paths.

These are templates, not assumptions about user preference. Default initial active profile is `Default`.

Requirements:

- Create, rename, clone, edit, delete and activate profiles.
- Preview profile diff before activation.
- Profile activation uses the same dry-run/transaction/rollback flow as rule edits.
- Profile state persists across reboot only after successful confirmation.
- Export/import profiles with schema/version, checksum and validation.
- No profile may remove SSH recovery exceptions or disable the serial console invariant.
- Do not store secrets, private keys or remote-access passwords in firewall profiles.

---

# 12. Application/backend security architecture

The PWA/GTK interface must never execute arbitrary privileged shell commands.

Create or extend a privileged backend daemon consistent with Nuxel’s existing `NuxelHost`, Bridge, D-Bus and service architecture.

Recommended logical service: `org.nuxel.Firewall` (choose a stable bus name and keep it consistent).

Possible service responsibilities:

- Read-only `GetStatus`, `GetPolicy`, `GetBackendCapabilities`, `GetInstalledApps`, `GetInterfaces`, `GetListeners`, `GetRules`, `GetLogs`, `GetProfiles`, `GetPendingTransaction`.
- Mutating `ValidatePolicy`, `DryRun`, `Apply`, `Confirm`, `Rollback`, `SetAppRule`, `SetServiceRule`, `SetDirectionDefaults`, `ActivateProfile`, `ExportPolicy`, `ImportPolicy`, `Enable`, `Disable`.
- Every mutating request must validate caller authorization, input schema, ownership, and current transaction state.
- Use polkit or the project’s established privileged-action authorization model. No world-writable control socket.
- A PWA can only call named methods with structured arguments. Never accept arbitrary shell command text, rule snippets, nftables expressions, file paths or unit names from UI input.
- Construct subprocess arguments as arrays; never interpolate user input into a shell command.
- Validate CIDRs using a real IP parser, port ranges as integers, interface IDs against discovered interfaces, app IDs against the canonical registry, and protocols against a strict enum.
- Apply root-owned state/config permissions; use atomic file replacement and fsync for persistent policy updates.
- Audit every privileged mutation with actor, timestamp, transaction ID, operation, old/new policy hashes, result and backend evidence. Do not include secrets.
- Use a lock to serialize apply/rollback/profile/network-event changes.
- D-Bus/API errors must return a structured refusal; the UI must never optimistically report success.

Implement AppArmor policy updates for the daemon/app if the repository’s LSM path requires them. Do not accidentally give the UI process direct write access to `/etc`, nftables netlink, `/var/lib/nuxel/firewall`, or systemd management.

## 12.1 Suggested persistent paths

Follow the repository’s single-source `paths.conf` convention and adjust to canonical Nuxel paths, but maintain clear separation:

- Read-only shipped defaults under `/usr/share/nuxel/...` or repository `configs/...`.
- Owner policy under `/etc/nuxel/firewall/` or the established Nuxel persistent config path.
- Runtime status and pending transaction under `/run/nuxel/firewall/`.
- Last-known-good, backups, audit and bounded logs under `/var/lib/nuxel/firewall/`.
- Temporary dry-run renders under `/run/nuxel/firewall/dry-run/`.

Do not make the repository checkout writable at runtime. Do not store the authoritative user policy in the PWA’s localStorage.

## 12.2 CLI integration

Provide a small, documented CLI for recovery and diagnostics, reusing the existing script where appropriate:

```text
nuxel-firewall status
nuxel-firewall backend-probe
nuxel-firewall apps
nuxel-firewall rules
nuxel-firewall dry-run
nuxel-firewall apply --rollback-after 60
nuxel-firewall confirm
nuxel-firewall rollback
nuxel-firewall profile list
nuxel-firewall profile activate <profile-id> --dry-run
nuxel-firewall evidence
nuxel-firewall self-test
```

CLI `apply` must obey the same SSH guard, backend ownership, dry-run, snapshot, confirmation and rollback requirements as the UI. Do not create a second code path with weaker safety.

---

# 13. Systemd lifecycle and boot behavior

Integrate with the existing `configs/nftables/systemd/nuxel-firewall.service` rather than creating duplicate services.

- Keep the service ordering compatible with NetworkManager, SSH, Nuxel Bridge/Portal and remote-desktop components.
- Load the last-known-good confirmed policy at boot.
- Validate that the selected backend and required kernel features are available before claiming the service started successfully.
- Do not load a pending/unconfirmed policy at boot.
- If the backend is unavailable, report `NOT ENFORCED`/`DEGRADED`; do not claim `ACTIVE`.
- The daemon should handle network changes without full ruleset replacement.
- Ensure reboot and daemon restart do not duplicate rules.
- Ensure VPN state changes do not remove SSH allow rules or remote-service safeguards.
- Ensure service stop/restart does not globally flush Netfilter state.
- Keep systemd hardening (NoNewPrivileges where possible, ProtectSystem, ProtectHome, ReadWritePaths, DevicePolicy, capability bounding) consistent with the privileged operations actually required. Do not blindly apply a sandbox setting that prevents the daemon from using netlink or systemd APIs.
- Install/uninstall/upgrade scripts must preserve user policy and backups. Package removal must not leave a misleading “active” indicator or orphaned global rules.

On first installation, do **not** silently enable a restrictive firewall while the owner is connected remotely. Run discovery + dry-run first, prepare the management allowlist, then wait for an explicit activation action. If an older Nuxel firewall is already active, migrate it with snapshot + rollback; do not disable protection blindly.

---

# 14. Settings and Quick Settings integration

## Settings → Security

Add a Firewall section/card with:

- Current active/inactive status (queried from daemon/live kernel).
- Selected backend and capability level.
- Inbound / outbound / forward summary.
- `Open Firewall` action to the full app.
- A compact `Last applied`/`Unconfirmed changes` status.

Do not build a second policy editor inside Settings. The full Firewall app is the only authoritative UI.

## Quick Settings tile

- Use the existing `23-firewall.png` asset.
- Distinguish active, inactive, degraded and unconfirmed states.
- A quick toggle must use the daemon transaction API and preserve the management whitelist.
- If a transaction is pending, tapping the tile must not disarm rollback or report a false success.
- Long press opens the full Firewall app.
- The tile must work after reboot and reflect real enforcement readback.

## Notifications

Optional notification channels:

- Firewall state changes.
- Unconfirmed apply countdown.
- Blocked traffic (rate-limited and configurable).
- Backend/capability failure.
- Newly installed app detected.

Do not flood the user with a notification for every blocked packet.

---

# 15. First-run setup and migration flow

The first-run experience should be short and safety-focused:

1. Detect active firewall backend(s), kernel, netfilter features, current rules, active network and listeners.
2. Show what is currently managing the firewall and whether multiple managers conflict.
3. Discover the current SSH connection/allowed sources, and show the proposed exact rule.
4. Prepare XRDP/VNC service profiles without starting those services or exposing their ports.
5. Show current installed apps and network identity coverage.
6. Migrate existing explicit `public`/`isolated` policies and sandbox network restrictions safely.
7. Show the requested initial defaults: inbound deny, forwarding deny, outbound allow.
8. Run a full dry-run and show the changes.
9. Offer a safe Apply-with-rollback action.
10. Require a successful health check and explicit confirmation before recording the new policy as last-known-good.

Do not automatically install or start a firewall manager in this flow. If no backend exists, provide a clear dependency status and a package-manager-specific installation suggestion, but do not execute it without explicit owner authorization.

---

# 16. Verification and testing — required, not optional

The current mock-nft suite is useful but does not prove kernel syntax or real packet behavior. Extend the suite and add real integration evidence.

## 16.1 Unit/schema tests

- Policy schema validation.
- Valid/invalid IPv4 and IPv6 CIDRs.
- Valid/invalid ports/ranges and protocol names.
- Stable app ID and cgroup identity normalization.
- Collision detection for class IDs and normalized cgroup names.
- Policy inheritance: global outbound allow; explicit deny overrides; strict allowlist mode; new apps inherit configured mode.
- Preserve explicit legacy isolated/deny rules during migration.
- Rule ordering for app deny before established-flow accept.
- LAN vs Wi-Fi destination classification and overlapping category semantics.
- VPN interface classification and down-state behavior.
- No unknown interface or missing backend silently becomes allowed when the effective policy requires deny.
- No user rule can delete or widen mandatory management policy without explicit confirmation.

## 16.2 Backend tests

For each implemented backend:

- Dry-run makes no live changes.
- Syntax/API validation works.
- Apply is idempotent.
- Existing foreign tables/chains remain unchanged.
- Rollback restores exactly the prior Nuxel-managed state.
- Failed apply leaves previous state intact.
- UFW/firewalld mutual conflict is detected.
- `iptables-nft` vs `iptables-legacy` is detected correctly.
- Unsupported backend features are reported, not simulated.
- Readback matches the intended policy.

## 16.3 Critical remote-access tests

Use mock listeners and controlled network namespaces/VMs first; then verify on the actual S10+ and target VM as available.

- SSH TCP 22 from a trusted source is allowed.
- SSH from an untrusted source is dropped.
- If port 2022 is not actually configured/listening, it is not opened.
- An existing SSH session survives apply.
- A second fresh SSH session from an allowed management source succeeds after apply.
- A source outside sshd `AllowUsers` cannot connect even if it reaches the listener.
- XRDP TCP 3389 is not exposed while XRDP is disabled.
- When XRDP starts through its owner action, the firewall rule is applied first and only allows verified trusted source ranges.
- VNC TCP 5900 is not exposed while wayvnc is disabled.
- VNC direct LAN access, when explicitly enabled, is source-limited; public/untrusted interface sources remain blocked.
- Loopback/SSH tunnel to `127.0.0.1:5900` and `127.0.0.1:3389` works where the services are active and SSH policy permits it.
- The serial recovery console is not touched.
- The known-panicking USB NCM path remains disabled.
- Simulate failed guard verification and prove rollback happens.
- Simulate apply timeout and prove rollback happens.
- Simulate PWA/daemon/UI crash during apply and prove rollback remains armed.
- Simulate reboot while an apply is unconfirmed and prove boot restores the last-known-good policy.

## 16.4 Packet behavior tests

Use Linux network namespaces/veth pairs, local test servers, counters and packet capture to verify:

- Input default drop for new TCP/UDP connections.
- Input established/related replies work.
- Output default allow works for normal TCP/UDP/ICMP as configured.
- App-level deny blocks both new and existing TCP flows.
- App-level deny blocks UDP, DNS direct queries, IPv6, alternate ports and direct-IP connections.
- App-level allow works only on the selected network category.
- LAN and Internet-over-Wi-Fi categories behave differently as specified.
- VPN-only traffic does not leak when the tunnel drops.
- IPv4 and IPv6 parity.
- DHCP, DNS resolver, IPv6 ND/RA/PMTU essential paths continue to work without granting blanket egress to blocked apps.
- Forwarding remains blocked unless explicitly enabled.
- Blocked-traffic logs and counters identify the right app where identity is verified.

## 16.5 Real app attribution tests

- Launch at least two independent native apps with different app IDs.
- Generate traffic from both to the same local test server.
- Allow app A, block app B.
- Show that only app A reaches the server; include evidence from cgroup membership and nft/iptables counters.
- Repeat with two network-capable PWAs. This test is mandatory before PWA matrix controls can be marked `Verified`.
- Test subprocesses, helper processes, network processes, and app restart.
- If per-app attribution is impossible for a runtime type, show that runtime type as unsupported instead of green.

## 16.6 UI and integration tests

- Firewall app appears in launcher/app drawer and opens successfully.
- Settings → Security entry opens the same app/policy.
- Quick Settings tile reflects real backend state.
- Search/filter/sort works with long app lists.
- App matrix is usable on the S10+ narrow screen with horizontal scroll and sticky app names/header.
- Per-column bulk actions work and show counts.
- Toggling a checkbox creates staged edits only; UI does not claim the kernel changed until Apply succeeds.
- Dry-run shows a complete diff and no mutation.
- Apply countdown displays; Confirm disarms rollback; Rollback restores the previous policy.
- An unsupported backend/capability cannot be rendered as successfully enabled.
- Profile activation, export/import, log filters, and status refresh work.

## 16.7 Regression and build gates

Run the repository’s relevant gates, including:

- Existing firewall test suite.
- New firewall daemon/API unit tests.
- Native/PWA packaging and registry verification.
- Existing Nuxel Settings tests.
- App registry consistency checks.
- Static analysis/lint/security scans.
- Build and smoke tests on the repository’s documented environment.
- Real `nft -c -f` and live netfilter tests on a compatible Linux VM/device.

Do not weaken or delete existing tests to make the new implementation pass. Update tests where behavior is deliberately changed, with a clear explanation and equivalent/new coverage.

---

# 17. Performance, resource and reliability requirements

Nuxel is a phone OS. The firewall must not make the UI sluggish or burn battery.

- Use nftables sets/maps and counters rather than one huge rule per app per interface where avoidable.
- Do not poll the full ruleset continuously. Subscribe to events or refresh at sensible intervals.
- Keep the UI responsive while large app lists are loaded.
- Paginate/virtualize the app list if needed.
- Limit log volume and use journald/ring-buffer retention.
- Avoid expensive DNS lookups or reverse lookups in packet logging.
- Network changes should update only the necessary set entries.
- Rule compilation and dry-run should run in a worker/task, not block GTK/WebKit rendering.
- Use stable deterministic IDs so policy diffs are compact and backups are reproducible.
- Recover from daemon restart without duplicate chains, stale timers or stale pending state.

---

# 18. UI design and interaction quality bar

Use Nuxel’s existing visual language, penguin/arcade identity and phone-first design. Do not turn the app into a giant desktop firewall form.

- Strong shield state at the top; restrained colors, clear contrast and readable labels.
- Reuse supplied Nuxel app and Quick Settings firewall artwork.
- Compact AFWall-style matrix with clear columns, app icons, search and bulk controls.
- Use icon + text in column headers; do not rely on icon-only labels for accessibility.
- Touch controls must be comfortable and not overlap the scroll gesture.
- Preserve scroll position when an app setting changes or the list refreshes.
- Make staged vs applied changes obvious.
- Make rollback countdown highly visible and impossible to mistake for a normal toast.
- Confirm destructive operations with a readable explanation, not a generic browser `confirm()`.
- Include useful empty/error/loading states.
- Avoid fake packet graphs, placeholder app icons, dummy counters and hardcoded “active” examples.
- Display real backend evidence only.

Suggested UI surfaces:

**Apps** — main AFWall-inspired app/network matrix.

**Inbound** — SSH, XRDP, VNC and other listening services, with trusted sources/interfaces.

**Rules** — explicit rules with direction/action/order and edit capabilities.

**Networks** — live interface cards, trust classification, routes, VPN state and LAN prefixes.

**Profiles** — named policy profiles and their summaries.

**Logs** — blocked traffic, counters, app identity and filters.

**Advanced** — backend diagnostics, IPv4/IPv6 status, kernel/cgroup identity status, VPN kill switch, blocklists/hosts, policy import/export, audit and actual kernel rules.

---

# 19. Deliverables

Implement and commit the actual working pieces (unless the coding environment requests a different workflow):

1. Firewall app frontend and its launcher registration.
2. Settings → Security integration and Quick Settings tile integration.
3. Privileged firewall daemon / Bridge API / D-Bus interface.
4. Canonical policy schema, default policy, persistent state, migration and profiles.
5. Backend abstraction with the supported nftables implementation and safe UFW/firewalld/iptables detection/adapters as capability allows.
6. Corrected nftables policy that no longer flushes the entire ruleset and no longer relies on an early accept base chain to bypass later drops.
7. Correct app identity/cgroup/network attribution, including PWA process/network isolation or honest unsupported reporting.
8. Safe SSH/XRDP/VNC allowlist preparation and remote service lifecycle integration.
9. Mandatory dry-run, transactional Apply, confirmation, persistent rollback and last-known-good boot recovery.
10. Logs, counters, active rules view, rule editor, import/export and blocklist/hosts handling.
11. Systemd units/drop-ins, polkit/D-Bus policy, AppArmor profiles and package/build integration as required.
12. Automated tests and live evidence.
13. Documentation: user guide, backend/capability matrix, remote-access safety, migration, CLI recovery, troubleshooting and known limitations.

Update the app registry’s `required_apps_not_yet_in_tree` entry so Firewall manager is marked complete only after the actual app, backend and tests exist. Record the final app path and ledger reference rather than leaving the concept-level placeholder.

---

# 20. Required implementation sequence

Follow this order. Do not enable the firewall first and figure out access afterward.

### Phase A — Inspect and baseline

- Re-read the current source files and tests listed in §1; the repository may have changed since the supplied archive.
- Inventory active firewall managers and live rules.
- Inventory active interfaces/routes/listeners and remote-access policies.
- Record current SSH source/port/interface and verify serial console recovery availability.
- Establish the live baseline in an evidence directory.

### Phase B — Correct backend architecture

- Remove global ruleset flush behavior.
- Resolve the multi-base-chain guard flaw.
- Establish one authoritative manager/adapter and the Nuxel-owned rules namespace.
- Implement feature probes and truthful capability reporting.
- Implement reliable app identity attribution and the PWA isolation fix or honest limitation.

### Phase C — Policy model and engine

- Implement the direction defaults (INPUT drop, FORWARD drop, OUTPUT accept).
- Implement global outbound allow/block mode and per-app overrides.
- Implement network categories and routes.
- Implement SSH/XRDP/VNC prepared service rules with exact trusted-source restrictions.
- Implement logs, counters and profile model.

### Phase D — Safe apply system

- Implement dry-run, exact diff, syntax/API checking, snapshot, pending transaction, rollback timer, health verification and confirm.
- Implement boot-time last-known-good recovery.
- Add serial-console CLI recovery.
- Test all failure paths before using the real device.

### Phase E — App and settings UI

- Build the matrix, search, filter, bulk actions, rules, inbound services, profiles, logs and diagnostics.
- Add Settings and Quick Settings integration.
- Verify touch UX at phone dimensions.

### Phase F — Migration and installation

- Migrate existing app/network class policies without silent privilege expansion.
- Add app registration/package/service files.
- Test install/upgrade/reboot/uninstall behavior.
- Do not auto-enable on the real device during packaging. First run preview and remote safety validation first.

### Phase G — Verification and report

- Run all automated tests and real backend tests.
- Prove a new trusted SSH connection succeeds after policy activation.
- Prove a disallowed inbound connection fails.
- Prove outbound default is allow and outbound strict mode can block.
- Prove per-app native/PWA packet attribution for every runtime marked supported.
- Prove rollback after timeout and reboot during a pending transaction.
- Capture exact backend version, `nft list ruleset` or equivalent manager state, counters, service states and test results.

---

# 21. Acceptance criteria — completion means all applicable items pass

The implementation is not complete until:

- [ ] A real Nuxel Firewall app exists in the launcher and opens on device.
- [ ] Settings → Security and Quick Settings point to the same authoritative firewall service.
- [ ] UI status is derived from live backend readback, not saved settings.
- [ ] Inbound defaults to deny.
- [ ] Forwarding defaults to deny.
- [ ] Outbound defaults to allow.
- [ ] The owner can switch outbound to deny-by-default/allowlist mode.
- [ ] All installed apps appear once in the app list with stable IDs.
- [ ] Per-app network controls work at the actual socket-producing process for every runtime marked supported.
- [ ] New apps inherit the configured global outbound default.
- [ ] Existing explicit legacy app blocks are preserved through migration.
- [ ] LAN, Wi-Fi, Cellular, VPN/Mesh, USB and Wired categories are based on verified runtime routes/interfaces; unsupported categories are clearly disabled.
- [ ] IPv4 and IPv6 rules are both verified.
- [ ] Per-app deny blocks existing connections and cannot be bypassed by an established-flow shortcut.
- [ ] SSH port/source/interface allow rules are prepared before the first activation.
- [ ] Current SSH remains connected during apply.
- [ ] A fresh SSH connection from an authorized management peer succeeds after apply.
- [ ] Port 2022 is not opened unless an actual listener/configuration requires it.
- [ ] XRDP 3389 is not exposed while the service is disabled and is restricted to trusted sources when enabled.
- [ ] VNC 5900 is loopback/SSH-tunnel-only by default or, if owner explicitly chooses direct access, restricted to verified trusted LAN/mesh sources with an unencrypted-service warning.
- [ ] No SSH/XRDP/VNC port is opened to public Internet or cellular WAN by default.
- [ ] The serial recovery console remains untouched.
- [ ] The known-bad USB NCM path remains unavailable/disabled unless independently revalidated.
- [ ] Dry-run performs no live mutation and produces a complete readable plan.
- [ ] Apply requires a valid backend preflight and a prepared remote-management allowlist.
- [ ] Apply is transactional and starts an independent rollback timer before mutation.
- [ ] Confirm disarms rollback and records last-known-good state.
- [ ] Timeout, failure, crash or reboot while pending restores the previous confirmed policy.
- [ ] The implementation never globally flushes nftables/iptables state.
- [ ] UFW/firewalld/nftables/iptables conflicts are detected and not silently stacked.
- [ ] Unsupported app/network/backend capability is shown as unsupported, never green.
- [ ] The actual active ruleset, relevant service states, tests and limitations are included in the completion report.

If something cannot be implemented or proven on the Samsung Linux 4.14.253 kernel, say exactly what is missing and keep the UI honest. Do not claim a feature is complete based on generated rules or a passing mock test alone.

---

# 22. Final agent report format

At completion, return:

1. **Implemented:** concrete files, services, UI panels, app registration and backend adapters changed/added.
2. **Policy defaults:** confirm INPUT drop, FORWARD drop, OUTPUT allow and configurable strict mode.
3. **Backend:** selected backend, version, kernel capabilities, IPv4/IPv6 coverage, and whether UFW/firewalld/iptables conflicts were found.
4. **Remote access:** exact SSH allowlist/port/interface/source ranges discovered on the test device; XRDP/VNC prepared/active states; proof that a fresh trusted SSH connection works after apply.
5. **App attribution:** counts of native/PWA/Flatpak apps with verified, unsupported and unknown enforcement; evidence for one allow/one deny test.
6. **Dry-run/apply/rollback:** evidence for no-mutation dry-run, transaction snapshot, 60-second rollback, confirm, timeout rollback and pending-reboot recovery.
7. **Tests:** exact command and pass/fail counts; distinguish mock tests from real kernel/network tests.
8. **Known limitations:** every capability not verified, especially cgroup-v1 support, PWA network process separation, and any external firewall manager limitations.
9. **Recovery:** exact CLI/serial recovery command and location of last-known-good snapshot.

Do not say “fully working,” “secure,” “active,” “per-app protected,” or “SSH safe” unless the corresponding behavior has been tested and the live backend readback supports that claim.

---

# Reference material reviewed

Use these sources for technical/API details and verify the current documentation while implementing:

- AFWall+ source and feature overview: https://github.com/ukanth/afwall
- AFWall+ usage/FAQ (per-app network columns, whitelist/blacklist, Apply, profiles and active rules): https://github.com/ukanth/afwall/wiki/faq
- AFWall+ current Play Store feature list: https://play.google.com/store/apps/details?id=dev.ukanth.ufirewall
- nftables official man page, including verdict and base-chain evaluation semantics: https://netfilter.org/projects/nftables/manpage.html
- nftables base chain and priority documentation: https://wiki.nftables.org/wiki-nftables/index.php/Configuring_chains
- firewalld architecture and D-Bus management model: https://firewalld.org/documentation/architecture.html
- firewalld documentation (zones, runtime/permanent configuration, services and policies): https://firewalld.org/documentation/index.html
- firewalld backend configuration: https://firewalld.org/documentation/man-pages/firewalld.conf
- Ubuntu security documentation explaining Netfilter, nftables, iptables and UFW frontend relationships: https://documentation.ubuntu.com/security/security-features/network/firewall/
- UFW man page including dry-run and directional default policies: https://manpages.ubuntu.com/manpages/resolute/man8/ufw.8.html

**Final instruction:** build this as a real Nuxel system feature. A beautiful AFWall-inspired matrix is only the front end; correctness is determined by the actual packet path, the real app identity, the chosen backend’s ownership, the live remote-access path, and successful rollback. Never trade the owner’s SSH/serial recovery access for a green firewall shield.
