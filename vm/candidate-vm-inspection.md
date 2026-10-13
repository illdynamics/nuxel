# Candidate VM Deep Inspection + Reuse Decision

> **Build group:** bg-02-inspection (briq-04 `vm-inspection` + briq-05 `reuse-decision`)
> **Agent:** construQtor — QonQrete run `20260819-023154-5ff2e447`, cycle-002, call `bg-02-inspection__call-aef89296` (cycle-001 call failed, draft only; completed/committed in cycle-002 repair)
> **Executed:** 2026-08-19 ~05:00–05:06 CEST (host `wicked`)
> **Method:** safe, **no-boot** inspection of every candidate `.utm` bundle in the UTM Documents directory.
> **Honesty rule:** every claim below is backed by a quoted host command + raw output captured this run.
> No PASS is fabricated. Anything that cannot be proven without booting is marked **NOT VERIFIED HERE**.

---

## 0. Executive summary (decision first)

- **Exactly one candidate bundle exists:** `nuxel-aarch64-phosh` (UUID `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`).
- **Classification: CURRENT + GENUINE NU XEL.** The guest disk that QEMU actually boots
  (`Data/disk-0.qcow2`) contains Fedora 43 (ARM64, kernel `6.17.1-300.fc43.aarch64`),
  Phosh, the Nuxel service stack (`nuxel-bridge`, `nuxel-http-bridge`, `nuxel-portal`,
  `nuxel-notifications`, `nuxel-web`, `nuxel-phosh-agent`), the PWA (`/pwa/nuxel-home/`),
  D-Bus names `org.nuxel.*`, an AppArmor profile, and an nftables rules file.
- **Decision (briq-05): REUSE / REPAIR `nuxel-aarch64-phosh`. Do NOT create a duplicate VM.**
  Justification in §6.
- The five historical VMs from `finish/nuxel-ultimate-build.md` Part 10 (`Nuxel`,
  `Nuxel-phase1`, `Nuxel-PWA`, `Nuxel-checkpoint`, `Nuxel-wuuut`) are **no longer present**
  in the UTM Documents directory (§2).

---

## 1. Host & UTM recon (evidence)

| Item | Command | Result |
|---|---|---|
| Host arch | `uname -m` | `arm64` |
| macOS | `sw_vers` | `ProductName: macOS` / `ProductVersion: 15.7.5` / `BuildVersion: 24G624` |
| UTM app | `ls -ld /Applications/UTM.app` | present (drwxr-xr-x, Sep 15 2025) |
| UTM version | `defaults read /Applications/UTM.app/Contents/Info.plist CFBundleShortVersionString` | `4.7.4` (utmctl version also `4.7.4`) |
| Registered VMs | `/Applications/UTM.app/Contents/MacOS/utmctl list` | `711988C4-B34A-4A0F-BA86-B2C4A182E4BE  started  nuxel-aarch64-phosh` |
| VM status | `utmctl status "nuxel-aarch64-phosh"` | `started` |
| Documents dir | `ls -lah ~/Library/Containers/com.utmapp.UTM/Data/Documents/` | `Public/` (README.txt only) + `nuxel-aarch64-phosh.utm/` |
| All `.utm` bundles | `find ~/Library/Containers/com.utmapp.UTM/Data/Documents -maxdepth 1 -name "*.utm" -type d` | exactly one: `.../nuxel-aarch64-phosh.utm` |

Note: the VM is currently `started` (started by parallel group bg-04 before this
inspection ran). This inspection is read-only and does not start/stop anything.
The `stopped` pre-start gate is a creation-time requirement (Part 12 step 3), not a
statement about the current runtime state; that gate's history is recorded in
`vm/bg01-verify-creation-evidence.md` and `vm/utm-start-bg02-evidence.md`.

---

## 2. Candidate inventory

| # | Bundle | Path | Present? |
|---|---|---|---|
| 1 | `nuxel-aarch64-phosh.utm` | `~/Library/Containers/com.utmapp.UTM/Data/Documents/nuxel-aarch64-phosh.utm` | **YES — the only candidate** |
| — | `Nuxel`, `Nuxel-phase1`, `Nuxel-PWA`, `Nuxel-checkpoint`, `Nuxel-wuuut` | (historical, Part 10 of `finish/nuxel-ultimate-build.md`) | **GONE** — not in Documents dir; only `Public/README.txt` (UTM shared-dir placeholder) remains |

The UTM container's `Documents/Public/README.txt` is UTM's "no shared directory selected"
placeholder and contains no VM.

---

## 3. Deep inspection — `nuxel-aarch64-phosh` (the only candidate)

### 3.1 Bundle layout (host-side, verbatim `ls -lah`)

```
nuxel-aarch64-phosh.utm/
├── config.plist                                 3.6K  Aug 19 01:30   ← active config
├── config.plist.pre-bg04-1787095681.bak         3.2K  Aug 19 01:28   ← prior config (no ci-seed CD)
├── screenshot.png                                19K  Aug 19 04:31   ← UTM window screenshot (1280x800)
├── Data/
│   ├── disk-0.qcow2                              4.9G Aug 19 04:57   ← ACTIVE boot disk (growing, in use)
│   ├── efi_vars.fd                               1.1M Aug 19 04:40   ← ACTIVE EFI varstore (in use)
│   └── ci-seed.iso                              900K  Aug 14 04:17   ← cloud-init seed (attached as CD)
└── Data.utm/
    ├── Images/                                      (empty — stale baseline removed 2026-08-19 05:33, executing this doc's §6 recommendation)
    └── efi_vars.fd                              322K  Aug 14 00:25   ← STALE baseline (NOT opened by QEMU)
```

### 3.2 `config.plist` (active, parsed)

| Field | Value | Notes |
|---|---|---|
| Name / UUID | `nuxel-aarch64-phosh` / `711988c4-b34a-4a0f-ba86-b2c4a182e4be` | matches `utmctl list` |
| Backend / ConfigVersion | `QEMU` / 4 | |
| Architecture / Target | `aarch64` / `virt` | ARM64 (`qemu-aarch64-softmmu` confirmed in live process) |
| CPU | `max`, 4 cores (`CPUCount 4`, sockets=1, cores=4) | `-accel hvf` (Apple Hypervisor) |
| RAM | `8192` MiB | `-m 8192` in live process |
| Display / GPU | `virtio-gpu-gl-pci`, `ResolutionX 720`, `ResolutionY 1440`, DynamicResolution=false | **phone resolution 720×1440**; GL enabled |
| Network | `virtio-net-pci`, Mode `Shared` (`vmnet-shared`), `IsolateFromHost=false`, MAC `52:54:00:A1:6A:6B`, PortForward `[]` | no host→guest port forwards configured |
| Drives | (1) Disk `disk-0.qcow2`, VirtIO, read-write; (2) CD `ci-seed.iso`, VirtIO, read-only | CD was added in the current config (absent in `.pre-bg04` backup) |
| UEFI | `UEFIBoot=true`, pflash code from UTM cache (`edk2-aarch64-code.fd`, readonly), varstore `Data/efi_vars.fd` | |
| Serial | Terminal mode (Auto target) | |
| Sound | `[]` (none) | `-audio none` |
| Sharing | Clipboard off, DirectoryShareMode None | |
| Other | RNGDevice true, TPM off, Balloon off, PS2 off | |

### 3.3 EFI variable store

| File | `file` magic | `qemu-img info -U` (virtual/disk size) | In use? |
|---|---|---|---|
| `Data/efi_vars.fd` | `QFI` (qcow2) | 64 MiB virtual / 1.12 MiB allocated, compat 1.1, **corrupt: false** | **YES** — opened as `-drive if=pflash,unit=1` by live QEMU |
| `Data.utm/efi_vars.fd` | `QFI` (qcow2) | 64 MiB virtual / 324 KiB allocated, compat 1.1, corrupt: false | **NO** — stale |

### 3.4 Disk images

| File | Format | Virtual size | Allocated | Valid? | In use? | Content |
|---|---|---|---|---|---|---|
| `Data/disk-0.qcow2` | qcow2 v3 (QFI) | 17 GiB (18,253,611,008 B) | 5.06 GiB | yes (`corrupt: false`) | **YES — the booted disk** (open FD in QEMULauncher, `-drive ... Data/disk-0.qcow2`) | Fedora 43 + Phosh + **full Nuxel stack** (§3.5) |
| `Data.utm/Images/disk-0.qcow2` | qcow2 v3 (QFI) | 17 GiB | 520 MiB | yes | **NO** | **REMOVED 2026-08-19 05:33 — no longer present** (was Fedora-Cloud-only baseline, 0 nuxel / 0 phosh strings, §3.5) |
| `artifacts/vm/nuxel-aarch64.qcow2` | qcow2 v3 (QFI) | 17 GiB | 520 MiB | yes | no (artifact) | surviving copy of the removed baseline (was byte-identical to `Data.utm/Images/disk-0.qcow2`; SHA-256 `a4dd3e61…4bab9e6`, verified present) |

**GPT layout of the active disk** (parsed from raw conversion):

| Partition | Type GUID | Name | Start (sector) | Size |
|---|---|---|---|---|
| 1 | `28732ac1-1ff8-d211-ba4b-00a0c93ec93b` (ESP) | `UEFI` | 2048 | ~101 MiB |
| 2 | `bc13c2ff-59e6-4262-a352-b275fd6f7172` (XBOOTLDR) | `lxboot` | 206848 | ~2.05 GiB |
| 3 | `b921b045-1df0-41c3-af44-4c6f280d3fae` (**Linux root ARM64**) | `lxroot` | 4308992 | ~17.0 GiB |

→ `b921b045-…` is the **Linux root (ARM 64)** GUID: hardware-confirms this is an ARM64 guest root.

### 3.5 Guest content evidence (strings scan of read-only raw snapshot)

> Method: `qemu-img convert -U -S 4k -O raw <active qcow2> /tmp/…/active-disk.raw` (sparse, ~5.1 GiB
> real data) then `strings -a -n 6` → 19,170,838 lines; greps below. libguestfs/guestfish is **not
> installed** on this host, so a full file listing was not possible — see §5 limitations.

> **NOT VERIFIED HERE:** every guest-content claim in this section (and the verdicts in §3.7)
> is derived from a `strings` scan of a **live, in-use qcow2 snapshot** taken with
> `qemu-img convert -U` while the VM was running — it is not this group's runtime verification
> and may reflect a mid-write, inconsistent snapshot. See §5 Limitations.

**OS / kernel / boot chain (active disk):**
- Fedora 43 markers: `# Linux/arm64 6.17.1-300.fc43.aarch64 Kernel Configuration`,
  `.vmlinuz-6.17.1-300.fc43`, `initramfs-6.17.1-300.fc43.aarch64.img`, `VERSION_ID=…` (fc43 debug packages).
- UEFI boot chain: `BOOTAA64.EFI`, `EFI/BOOT/`, `EFI/fedora/`, `grubaa64.efi`, `shimaa64.efi`,
  `grub.cfg`, `grub2-efi-aa64`.

**Phosh (active disk) — INSTALLED:**
- `/usr/libexec/phosh`, `/usr/bin/phosh-mobile-settings`, `/usr/bin/phosh-osk-stevia`,
  `/usr/lib64/phosh/plugins/*` (launcher-box, calendar, media-players, location, …),
  `.gresource.phosh`, user unit `/home/nuxel/.config/systemd/user/phosh-resolution.service`.
- `phosh` case-insensitive string count: **7,924**.

**Nuxel stack (active disk) — INSTALLED (strings-scan evidence; NOT VERIFIED HERE at runtime):**
- systemd units: `/etc/systemd/system/nuxel-bridge.service`, `nuxel-http-bridge.service`,
  `nuxel-portal.service`, `nuxel-notifications.service`, `nuxel-web.service`,
  `nuxel-apparmor-enforce.service`; user unit `/home/nuxel/.config/systemd/user/nuxel-phosh-agent.service`.
- Journal (previous boots) shows **all started** — strings-scan evidence from a live-disk
  snapshot, NOT VERIFIED HERE (this group did not boot or run the guest):
  `Started nuxel-bridge.service - Nuxel Bridge D-Bus Permission Broker.`,
  `Started nuxel-http-bridge.service - Nuxel HTTP Bridge API.`,
  `Started nuxel-portal.service - Nuxel Portal Daemon.`,
  `Started nuxel-notifications.service - Nuxel Notification Hub.`,
  `Started nuxel-web.service - Nuxel PWA Static Web Server (nuxel-home launcher on :8000).`,
  `Started nuxel-phosh-agent.service - Nuxel Phosh Agent`.
- D-Bus names claimed (journal) — strings-scan evidence only, NOT VERIFIED HERE
  (no D-Bus tree was exercised by this group): `org.nuxel.Bridge` (02:40:18), `org.nuxel.Portal` (02:40:18,
  re-claimed 02:43/02:47/02:52), `org.nuxel.Notifications` (02:40:18),
  `org.nuxel.PhoshAgent` (session bus, multiple runs 00:22–00:30).
- PhoshAgent flow evidence (journal): permission request `org.nuxel.home / location` →
  `Permission result … granted=False`; notifications `NotificationAdded` from `org.nuxel.home`
  ("VM verify signal test"); `Gtk couldn't be initialized` (display absent) warnings in
  **earlier headless runs** — i.e., pre-display runs failed gracefully, and later runs had a session.
- Deploy evidence: `/home/nuxel/nuxel/vm/nuxel-vm-bootstrap.sh`,
  `/home/nuxel/nuxel/vm/vm-verify-services.sh`, `/home/nuxel/nuxel/vm/vm-verify-phosh-agent.sh`
  all executed (sudo audit `AUDIT_FIELD_CMD` records); deploy manifest in repo:
  `git_rev=b4f548e497f9f9768f6ff3796d955c9895d202a7`, `deployed_at_utc=2026-08-19T00:46:03Z`.
- Python venv at `/opt/nuxel/.venv` (python 3.14 site-packages), repo mirror at `/home/nuxel/nuxel`.

**PWA (active disk) — INSTALLED:**
- `/pwa/nuxel-home/index.html`, `/pwa/nuxel-home/sw.js`, `/pwa/nuxel-home/manifest.json`,
  `/pwa/nuxel-home/js/bridge.js`, `/pwa/nuxel-common/bridge.js`,
  `nuxel-home-kiosk`, `nuxel-home-kiosk.service`, `nuxel-home-launcher`, `nuxel-home-native`,
  `nuxel-home-native.service`, `nuxel-home.desktop`.

**Security config (active disk) — CONFIGURED per strings scan (enforcement is runtime,
NOT VERIFIED HERE; see §5):**
- AppArmor: profile `/etc/apparmor.d/usr.bin.nuxel-home` + `/etc/systemd/system/nuxel-apparmor-enforce.service`
  with audit records `cat /sys/module/apparmor/parameters/enabled`,
  `ls /sys/kernel/security/apparmor/profiles`.
- nftables: `/usr/lib/systemd/system/nftables.service`, `/etc/nftables/` present; audit record
  `cmp -s /home/nuxel/nuxel/configs/nftables/nuxel-app-firewall.nft /etc/nftables.conf`
  (repo file `configs/nftables/nuxel-app-firewall.nft` exists, 6,160 B).
- SELinux: Fedora-default SELinux xattrs/strings present (661,506 `selinux` matches) — i.e.,
  Fedora defaults to SELinux; AppArmor enforcement therefore needs runtime confirmation.
- Browser landscape: `epiphany` + WebKit (`/usr/lib64/libwebkit2gtk-4.1.so.0.21.9`,
  `/usr/lib64/webkitgtk-6.0`) present; **no chromium / firefox binary found** in the guest.
  The kiosk script (`shell/nuxel-kiosk/nuxel-home-kiosk`) prefers `chromium-browser` →
  `chromium` → `firefox` (all absent) — a runtime risk for the kiosk path (bg-07 to verify).

### 3.6 Runtime state at inspection time (read-only)

- `utmctl list` / `utmctl status`: `started`.
- Live process: `QEMULauncher … qemu-aarch64-softmmu -machine virt -accel hvf -cpu max -smp cpus=4 …
  -m 8192 … -drive if=pflash,unit=1,file.filename=…/Data/efi_vars.fd …
  -drive if=none,media=disk,id=drive711988c4…,file.filename=…/Data/disk-0.qcow2 …
  -drive if=none,media=cdrom,id=drivecd-seed-nuxel,file.filename=…/Data/ci-seed.iso …` (UTM 4.7.4, started 04:40).
- `lsof` on QEMULauncher confirms the **only open** bundle files are:
  `Data/ci-seed.iso`, `Data/efi_vars.fd`, `Data/disk-0.qcow2` → the `Data.utm/*` copies are NOT in use.
- Guest reachability (host-side probe, no guest commands run): `ping 192.168.64.3` → 0% loss,
  `nc -z -G 2 192.168.64.3 22` → **ssh port open** (vmnet-shared network; IP matches
  `vm/utm-state-report.md` §4).
- Screenshot files (metadata only; pixel content not verifiable in this session):
  bundle `screenshot.png` 1280×800 (UTM window), `vm/screenshots/phosh-session-720x1440.png`
  **720×1440** (phone resolution).

### 3.7 Classification

| Axis | Verdict | Evidence basis |
|---|---|---|
| Genuine Nuxel vs Fedora+Phosh-only | **GENUINE NU XEL** | booted disk contains Nuxel systemd units, D-Bus `org.nuxel.*` claims, PWA files, PhoshAgent, deploy manifest, AppArmor profile, nftables rules — not just "Nuxel in the name / Phosh / 720x1440" |
| stale / experimental / current | **CURRENT** | disk actively written by the running VM (mtime 04:57, growing 4.9→5.06 GiB); services started in recent boots; guest SSH-reachable |
| Bootable | **YES (booted)** | live QEMU process + reachable SSH; UEFI chain (shim/grub/BOOTAA64 + vmlinuz/initramfs 6.17.1) present |
| Known stale components | `Data.utm/efi_vars.fd` (322K) + `config.plist.pre-bg04-1787095681.bak` | not opened by QEMU (lsof §3.6); baseline disk `Data.utm/Images/disk-0.qcow2` removed 2026-08-19 05:33 — `Data.utm/Images/` now empty (§3.1) |

> **NOT VERIFIED HERE:** the `GENUINE NU XEL` and `CURRENT` verdicts above rest on
> strings-scan evidence from a live in-use qcow2 snapshot (see §5 Limitations); service
> start journal entries, D-Bus `org.nuxel.*` claims, and AppArmor/nftables presence are
> from that scan, not from this group's runtime verification (delegated to bg-06/07/08).
---

## 4. Per-bundle inspection remainder

Only **one** candidate bundle exists in the UTM Documents directory:
`nuxel-aarch64-phosh.utm`. It is fully covered in §3 (bundle layout §3.1,
`config.plist` §3.2, EFI varstore §3.3, disks §3.4, guest content §3.5, runtime
state §3.6, classification §3.7). There is **no remainder**: the five historical
VMs (`Nuxel`, `Nuxel-phase1`, `Nuxel-PWA`, `Nuxel-checkpoint`, `Nuxel-wuuut`)
are absent from the Documents directory and are covered under §2 (not candidates).

---

## 5. Limitations

This inspection is intentionally **read-only / no-boot**. The following
limitations apply to the evidence above:

1. **No libguestfs / guestfish.** `guestfish`/`libguestfs` is **not installed** on
   this host, so a full, structured guest-file listing (ext4 mount + file walk)
   was not possible. Guest content evidence therefore relies on host-side strings
   scans of a raw disk snapshot rather than on a verified file listing.
2. **Live, in-use qcow2 snapshot (`qemu-img convert -U`).** The guest-content
   strings evidence was extracted from `Data/disk-0.qcow2` **while the VM was
   running**, using `qemu-img convert -U` (no exclusive write-lock taken; the
   converter reads without a consistent snapshot guarantee). The snapshot may be
   **mid-write / internally inconsistent** (the disk was observed growing
   4.9 → 5.06 → 5.8 GiB during the run). All §3.5/§3.7 content claims inherit
   this caveat and are marked **NOT VERIFIED HERE**.
3. **Runtime enforcement NOT verified by this group.** AppArmor/nftables
   *enforcement* (loaded profiles, active nftables ruleset) and pixel-level
   display content (Phosh rendering) were **NOT** verified from this group —
   these are delegated to the runtime build groups (bg-06 services/API/D-Bus,
   bg-07 Phosh/PWA, bg-08 security/smoke). This group only establishes that the
   *configurations are present on disk* (strings-scan evidence).
4. **Parallel-group state.** The inspection ran while bg-04 had the VM **started**
   (`utmctl status`: `started`; live QEMULauncher process). The `current/started`
   classification therefore reflects **parallel-group state, not this group's
   action** — this group started/stopped nothing. Guest-reachability probes
   (ping/ssh) are host-side observations of that parallel-started guest.
5. **Strings-scan false-positive risk.** A strings scan proves *bytes present on
   disk*, not that a service is currently running, enabled, or correct; journal
   and D-Bus-name claims (§3.5) are from previously written journal bytes, not
   from a live D-Bus tree or `systemctl` query executed by this group.

---

## 6. Decision (briq-05): reuse-vs-create recommendation

**Decision: REUSE / REPAIR `nuxel-aarch64-phosh`. Do NOT create a duplicate VM.**

**Evidence-based justification:**

1. **Single candidate bundle.** Exactly one `.utm` bundle exists in the UTM
   Documents directory (`nuxel-aarch64-phosh`, UUID `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`);
   the five historical VMs from `finish/nuxel-ultimate-build.md` Part 10 are
   **gone** from the Documents directory (§2). There is no other bundle to reuse.
2. **Genuine Nuxel content on the active booted disk.** The disk QEMU actually
   boots (`Data/disk-0.qcow2`) contains the full Nuxel service stack
   (`nuxel-bridge`, `nuxel-http-bridge`, `nuxel-portal`, `nuxel-notifications`,
   `nuxel-web`, `nuxel-phosh-agent` systemd units), `org.nuxel.*` D-Bus claims,
   the PWA at `/pwa/nuxel-home/`, Phosh, the deploy manifest
   (`git_rev=b4f548e…`), the AppArmor profile, and nftables rules — not merely
   "Nuxel in the name / Phosh / 720×1440" (§3.5). This is **strings-scan
   evidence from a live snapshot** and carries the §5 caveat (NOT VERIFIED HERE
   at runtime); the runtime groups (bg-06/07/08) verify actual execution.
3. **Registered and started.** The VM is registered with UTM and was `started`
   at inspection time (`utmctl list`/`utmctl status`; live `qemu-aarch64-softmmu`
   process, §3.6) — already beyond the Part-12 create-before-start gate.
4. **Stale components identified and excluded.** `Data.utm/efi_vars.fd` (322K)
   and `config.plist.pre-bg04-1787095681.bak` are **not** opened by the live
   QEMU process (lsof evidence, §3.6) and are excluded from the
   classification; the stale baseline disk `Data.utm/Images/disk-0.qcow2`
   (Fedora-Cloud-only, 0 nuxel / 0 phosh strings) was **removed 2026-08-19
   05:33** per this recommendation — `Data.utm/Images/` is now empty (§3.1, §3.4).
5. **Creation is unnecessary.** Because a genuine-Nuxel bundle exists, is
   registered, and is booted, re-creating a VM via `vm/build-vm-image.sh`
   would duplicate it without adding value. The correct action is to **repair/
   reuse** `nuxel-aarch64-phosh` (e.g., remove stale `Data.utm/*` and `.bak`
   components when the VM is stopped) and let the runtime groups verify the
   booted guest end-to-end.
