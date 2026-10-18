<!-- Nuxel v0.5.1-alpha -->
# Nuxel Security Model

> **Target: GrapheneOS-level hardening on a Linux-native substrate**
> **Device: Google Pixel 10 Pro XL (mustang) with Titan M3 security chip**

---

## 1. Overview

Nuxel applies defense-in-depth security across every layer — from hardware root of trust through kernel hardening, sandbox enforcement, portal mediation, and app confinement. The model is inspired by GrapheneOS's approach to Android hardening, adapted for a pure Linux stack with no Android dependencies.

### 1.1 Security Principles

1. **No ambient trust** — No app sees other apps' data, no ambient filesystem access, no ambient IPC, no background execution unless explicitly approved.
2. **Portals for all hardware access** — Apps ask for ACTIONS, not permanent permissions. Every camera capture, mic recording, location query, file access is gated through a portal dialog.
3. **Least privilege by default** — Apps start with zero capabilities. Every capability must be explicitly requested, explained to the user, and granted.
4. **Defense in depth** — Every layer enforces its own restrictions: namespaces, seccomp, Landlock, AppArmor, nftables, D-Bus policy, portals.
5. **No ambient network** — Apps have no network access by default. Outbound and inbound network are separate capabilities.
6. **Revocable by design** — Every grant can be revoked instantly. Revocation takes effect on the next request, no app restart needed.
7. **Auditable** — Every capability access is logged. Users can view their full permission history.

---

## 2. Sandbox Architecture

### 2.1 Layered Sandbox (Bubblewrap + Namespaces + seccomp + Landlock + AppArmor)

Every application (PWA or native GTK4) is confined by five mandatory layers:

#### Layer 1: Namespace Isolation (Bubblewrap)

```
Mount namespace:
  / → new root (tmpfs)
  ├── /usr    → bind mount (ro) from host /usr
  ├── /etc    → bind mount (ro) from host /etc  
  ├── /var/app/<app-id>/data/  → bind mount (rw) — app's own data
  ├── /dev    → minimal: null, zero, random, urandom, full
  ├── /proc   → new procfs (only this PID namespace)
  └── /tmp    → tmpfs (rw, size=256MB max)

PID namespace:  Only app's own processes visible
Net namespace:  Separate netns OR host netns with nftables rules
IPC namespace:  No System V IPC, no POSIX message queues
UTS namespace:  Isolated hostname
User namespace:  App runs as sandbox-user (UID 100000+), mapped to root in netns
```

#### Layer 2: seccomp BPF (Syscall Filter)

Default-deny with allow-listing per app category:

```c
// PWA category (most restricted)
Allowed syscalls: read, write, openat, close, mmap, munmap, mprotect,
                  brk, sched_yield, clock_gettime, getrandom, nanosleep,
                  futex, newfstatat, getdents64, writev, readv,
                  recvmsg, sendmsg (if network enabled), poll, epoll_wait

Blocked: ioctl (/dev/* nodes), ptrace, perf_event_open, bpf,
         __arm64_smccc_smc (EL3 calls), kcmp, process_vm_readv,
         process_vm_writev, mount, umount2, swapon, swapoff,
         create_module, init_module, finit_module, delete_module

// Native app category (broader)
Native apps additionally allowed: socket, bind, listen, connect,
                                   accept4, setsockopt, getsockopt
But still blocked: ptrace, perf_event_open, __arm64_smccc_smc
```

#### Layer 3: Landlock (Filesystem Restrictions)

```c
// Allowed accesses:
LANDLOCK_ACCESS_FS_READ_DIR | LANDLOCK_ACCESS_FS_READ_FILE:
  /usr (ro), /etc (ro), /var/app/<app-id>/data (rw)

LANDLOCK_ACCESS_FS_WRITE_FILE | LANDLOCK_ACCESS_FS_REMOVE:
  /var/app/<app-id>/data (rw)

LANDLOCK_ACCESS_FS_EXECUTE:
  /usr/bin (ro), /usr/lib (ro)

// Denied:
  /dev, /sys, /proc/<other-pids>, /var/app/<other-app-id>/
```

#### Layer 4: AppArmor (Mandatory Access Control)

Per-app profiles in `/etc/apparmor.d/`:

```
profile nuxel-pwa-org.example.myapp flags=(attach_disconnected) {
    #include <abstractions/base>
    #include <abstractions/nameservice>
    
    # App data directory
    /var/app/org.example.myapp/data/** rwk,
    
    # System libraries (read-only)
    /usr/lib/** r,
    /usr/share/** r,
    
    # Network — only if capability granted
    network inet stream,
    network inet dgram,
    
    # D-Bus
    dbus send bus=system path=/org/nuxel/Bridge interface=org.nuxel.Bridge member=*,
    dbus receive bus=system path=/org/nuxel/Bridge interface=org.nuxel.Bridge member=*,
    
    # Deny everything else
    deny /dev/** rwk,
    deny /sys/** r,
    deny /proc/*/mem rw,
    deny ptrace,
}
```

#### Layer 5: nftables (Network Isolation)

Per-app cgroupv2-based rules in `configs/nftables/nuxel-app-firewall.nft`:

```nftables
table inet nuxel_app_firewall {
    chain input {
        type filter hook input priority -100; policy drop;
        # Allow established connections
        ct state established,related accept
        # Allow loopback
        iif lo accept
    }
    
    chain forward {
        type filter hook forward priority -100; policy drop;
    }
    
    chain output {
        type filter hook output priority -100; policy drop;
        # Allow DNS
        udp dport 53 accept
        # Per-app allow rules (added dynamically)
        socket cgroupv2 level 2 "app-network-allowed" accept
    }
    
    chain prerouting {
        type nat hook prerouting priority -100; policy accept;
    }
    
    chain postrouting {
        type nat hook postrouting priority 100; policy accept;
    }
}
```

Dynamic rules added per app:
```bash
# Allow network for app with capability
nft add rule inet nuxel_app_firewall output \
    socket cgroupv2 level 2 "app-org.nuxel.mail" accept

# Block network for app without capability  
# (default rule drops, no accept rule added)
```

---

## 3. Portals Architecture

### 3.1 Standard Portals (xdg-desktop-portal)

| Portal | D-Bus Interface | Backend | User Experience |
|--------|----------------|---------|----------------|
| **Camera** | org.freedesktop.portal.Camera | PipeWire camera stream | GTK4 dialog: "App wants to take a photo" |
| **Microphone** | org.freedesktop.portal.Microphone | PipeWire audio capture | GTK4 dialog: "App wants to record audio" |
| **Location** | org.freedesktop.portal.Location | GeoClue2 | GTK4 dialog: "App wants your location" |
| **Notifications** | org.freedesktop.portal.Notification | nuxel-notifications | Silent: app sends notification |
| **FileChooser** | org.freedesktop.portal.FileChooser | Filesystem (userdata) | GTK4 file picker dialog |
| **Screenshot** | org.freedesktop.portal.Screenshot | Wayland ext-screencopy | GTK4 dialog: "App wants to capture screen" |
| **ScreenCast** | org.freedesktop.portal.ScreenCast | Wayland wlr-screencopy | GTK4 dialog: "App wants to record screen" |
| **Print** | org.freedesktop.portal.Print | CUPS | GTK4 print dialog |
| **Account** | org.freedesktop.portal.Account | AccountsService | Silent: app reads username |
| **Email** | org.freedesktop.portal.Email | Mail client | Opens default mail compose |
| **OpenURI** | org.freedesktop.portal.OpenURI | xdg-open | Opens URL in browser |

### 3.2 Nuxel-Specific Portals (nuxel-portal)

| Portal | D-Bus Interface | Backend | User Experience |
|--------|----------------|---------|----------------|
| **SMS** | org.nuxel.portal.SMS | ModemManager.Messaging | GTK4 dialog: "App wants to send SMS to +1555..." |
| **Call** | org.nuxel.portal.Call | ModemManager.Call | GTK4 dialog: "App wants to call +1555..." |
| **PhoneStatus** | org.nuxel.portal.PhoneStatus | ModemManager.Modem | Silent: app reads signal, operator |
| **ContactsLookup** | org.nuxel.portal.Contacts | EDS / nuxel-contacts | GTK4 dialog: "App wants to search contacts" |
| **SystemSettings** | org.nuxel.portal.Settings | GSettings | GTK4 dialog: "App wants to change display brightness" |

### 3.3 Portal Flow

```
1. App calls portal API (D-Bus or bridge method)
2. Portal daemon validates app identity
3. Portal shows GTK4/libadwaita dialog with:
   - App name and icon
   - What action the app wants
   - Duration: "Just once" / "Until I revoke" / "Always for this app"
   - [Deny] [Allow This Time] [Allow Always]
4. User response sent back to portal
5. If denied: error returned to app
6. If allowed: action is performed, result returned to app
7. "Allow Always" stores grant in /var/lib/nuxel/permissions/<app-id>.json
8. User can revoke at any time via Settings > Apps > [App] > Permissions
```

---

## 4. Exploit Mitigations

### 4.1 Memory Allocator Hardening

**hardened_malloc** from GrapheneOS, applied system-wide via `/etc/ld.so.preload`:

```
# /etc/hardened-malloc.conf
hardened_malloc_zero_on_free: true
hardened_malloc_canary: true  
hardened_malloc_guard_slabs: true
hardened_malloc_quarantine: true
hardened_malloc_quarantine_size: 16
hardened_malloc_large_config: true
hardened_malloc_handle_oom: abort
```

Features:
- **Zero-on-free** — All freed memory is immediately zeroed, preventing info leaks
- **Canary protection** — Heap buffer overflow detection with randomized canary values
- **Guard slabs** — Guard pages between slab allocations, catching overflows
- **Quarantine** — Freed chunks held before reuse, preventing use-after-free
- **Random slab allocations** — Slots randomly selected, not sequential

### 4.2 Compiler Hardening

All native code compiled with:

```bash
CFLAGS="-fPIE -pie \
        -fstack-protector-strong \
        -D_FORTIFY_SOURCE=3 \
        -fno-omit-frame-pointer \
        -fno-delete-null-pointer-checks \
        -fno-strict-overflow \
        -Werror=format-security \
        -Wp,-D_GLIBCXX_ASSERTIONS \
        -fno-plt \
        -fcf-protection=full"

# aarch64-specific
CFLAGS+=" -mbranch-protection=standard"  # PAC + BTI

# Linker
LDFLAGS="-Wl,-z,relro,-z,now,-z,noexecstack \
         -Wl,-z,separate-code \
         -Wl,--as-needed"
```

### 4.3 Kernel Hardening

Kernel config overrides for Nuxel (`kernel/defconfig` additions):

```
# Memory protections
CONFIG_STRICT_KERNEL_RWX=y
CONFIG_STRICT_MODULE_RWX=y
CONFIG_UNMAP_KERNEL_AT_EL0=y
CONFIG_HARDENED_USERCOPY=y
CONFIG_HARDENED_USERCOPY_PAGESPAN=y
CONFIG_RANDOMIZE_KSTACK_OFFSET_DEFAULT=y
CONFIG_INIT_ON_ALLOC_DEFAULT_ON=y
CONFIG_INIT_ON_FREE_DEFAULT_ON=y

# Control flow integrity
CONFIG_CFI_CLANG=y
CONFIG_CFI_PERMISSIVE=n
CONFIG_SHADOW_CALL_STACK=y
CONFIG_BTI=y

# Stack canaries
CONFIG_STACKPROTECTOR=y
CONFIG_STACKPROTECTOR_STRONG=y

# Pointer authentication
CONFIG_ARM64_PTR_AUTH=y
CONFIG_ARM64_PTR_AUTH_KERNEL=y

# Module signing
CONFIG_MODULE_SIG=y
CONFIG_MODULE_SIG_FORCE=y
CONFIG_MODULE_SIG_SHA512=y

# Executable space protections
CONFIG_EFI_DISABLE_PIC_DEFAULT=y
CONFIG_RANDOMIZE_BASE=y
CONFIG_RANDOMIZE_MODULE_REGION_FULL=y

# BPF hardening
CONFIG_BPF_JIT=y
CONFIG_BPF_JIT_ALWAYS_ON=y
CONFIG_BPF_UNPRIV_DISABLED=y

# Security hardening
CONFIG_SECURITY=y
CONFIG_SECURITY_APPARMOR=y
CONFIG_SECURITY_LANDLOCK=y
CONFIG_SECURITY_YAMA=y
CONFIG_SECURITY_NETWORK=y
CONFIG_SECURITY_NETWORK_XFRM=y

# SELinux (not used, but available)
# CONFIG_SECURITY_SELINUX is not set

# IOMMU
CONFIG_ARM_SMMU=y
CONFIG_ARM_SMMU_V3=y
CONFIG_IOMMU_DEFAULT_PASSTHROUGH=n
CONFIG_IOMMU_DEFAULT_DMA_LAZY=n
CONFIG_IOMMU_DEFAULT_DMA_STRICT=y
```

---

## 5. Storage Isolation

### 5.1 Per-App Storage Layout

```
/var/app/<app-id>/
├── data/             — App's writable data (IndexedDB, CacheAPI, configs)
│   ├── index.html
│   ├── sw.js
│   └── ...
├── config/           — App configuration (capability grants, preferences)
├── cache/            — App cache (ephemeral, can be cleared)
└── tmp/              — App temporary files (ephemeral, per-session)
```

### 5.2 Isolation Guarantees

- **No app can read another app's storage directory**
  - Landlock rules reject access to `/var/app/<other-app-id>/**`
  - AppArmor profile only allows `/var/app/<own-app-id>/**`
  - Bubblewrap mount namespace only maps the app's own directory
- **No ambient filesystem access**
  - Apps cannot list `/home/user/Documents/` without the file picker portal
  - File picker returns a read-only file descriptor, not a path
  - Even with the descriptor, Landlock prevents path-based access
- **Data directory is removed on uninstall**
  - Flatpak removal triggers `btrfs subvolume delete` or `rm -rf /var/app/<app-id>/`
  - No orphaned data left behind

---

## 6. Network Isolation

### 6.1 Per-App nftables Rules

Network is controlled via cgroupv2-based nftables rules:

```bash
# On app launch, if app has network capability:
cgcreate -g net_cls:app-org.nuxel.mail
cgset -r net_cls.classid=0x00010001 app-org.nuxel.mail
nft add rule inet nuxel_app_firewall output \
    meta cgroup 0x00010001 accept

# On app launch, if app does NOT have network capability:
# No rule added → default drop policy applies
```

### 6.2 Network Capabilities

| Capability | Effect | Risk |
|-----------|--------|------|
| `network:outbound` | Allow outbound TCP/UDP (DNS always allowed) | Low-Moderate — data exfiltration |
| `network:inbound` | Allow inbound TCP/UDP (listening sockets) | High — attack surface |
| No network | Only AF_UNIX sockets to nuxel-bridge | None |

### 6.3 DNS Handling

DNS is always allowed (port 53) for resolution, even for apps without network capability. This prevents network errors in no-network apps but does not allow data exfiltration — the resolved IPs are unreachable.

---

## 7. IPC Isolation

### 7.1 D-Bus Access

| Bus | Access | Reason |
|-----|--------|--------|
| System bus (`/run/dbus/system_bus_socket`) | **Native apps only** | Core phone apps need ModemManager, NetworkManager |
| Session bus (`$XDG_RUNTIME_DIR/bus`) | **Not mounted for PWAs** | PWA IPC only through nuxel-bridge Unix socket |
| nuxel-bridge socket (`/run/nuxel/bridge/<app-id>.sock`) | **Per-PWA unique socket** | Only the owning PWA can connect |

D-Bus policy enforcement:

```xml
<!-- System bus policy: nuxel-bridge -->
<policy context="default">
    <!-- Deny by default -->
    <deny send_destination="org.nuxel.Bridge"/>
    <deny receive_sender="org.nuxel.Bridge"/>
</policy>
<policy user="nuxel-bridge">
    <allow own="org.nuxel.Bridge"/>
    <allow send_destination="org.freedesktop.ModemManager1"/>
    <allow send_destination="org.freedesktop.NetworkManager"/>
    <allow send_destination="org.freedesktop.GeoClue2"/>
</policy>

<!-- Per-app policies via AppArmor dbus rules -->
```

### 7.2 Unix Socket Restrictions

- PWA sandboxes have NO access to `/run/dbus/` — cannot reach D-Bus at all
- The only socket in the sandbox is `/run/nuxel/bridge/<app-id>.sock` (mounted read-only)
- `AF_UNIX` `SOCK_DGRAM`/`SOCK_STREAM` only allowed to the bridge socket
- `AF_VSOCK`, `AF_NETLINK`, `AF_XDP` all blocked by seccomp

---

## 8. Display Isolation

### 8.1 Wayland Surface Isolation

- Each app gets its own `wl_surface` connection to phoc
- **No app can read another app's surface contents**
  - Wayland `wl_drm`/`zwp_linux_dmabuf` is per-client isolated
  - Compositor never shares buffer handles between clients
- **No screen capture without portal**
  - `wlr-screencopy` / `ext-image-capture-source` protocol requires compositor grant
  - Only the Screenshot/ScreenCast portal can request these
- **No input injection**
  - `zwp_virtual_keyboard_v1` and `zwp_virtual_pointer_v1` are compositor-blocked for sandboxed apps

---

## 9. Audio Isolation

### 9.1 PipeWire Per-App Streams

- Each app gets its own PipeWire stream node
- **No app can capture another app's audio output**
  - PipeWire loopback/loopback target not accessible from sandbox
  - `WP_NODE_*` filtering prevents cross-app stream access
- **Microphone access requires portal**
  - Portal opens the mic stream, returns a fd to the app
  - App cannot open `/dev/snd/*` directly — blocked by Landlock + seccomp
- **Audio routing is policy-based**
  - Calls get highest priority, ducking media
  - Notifications interrupt media briefly
  - All routing is compositor/pipewire-policy managed

---

## 10. Verified Boot Chain

### 10.1 Hardware Root of Trust: Titan M3

The Pixel 10 Pro XL's Titan M3 security chip provides:

- **Secure boot** — Boot ROM verifies XBL signature using fused OEM key
- **Rollback protection** — Version counter prevents downgrade attacks
- **Key attestation** — TPM-style key attestation for AVB
- **Rate limiting** — Brute-force protection for bootloader unlock attempts

### 10.2 Boot Chain Verification

```
Boot ROM (PBL)
  │
  ├── Reads XBL from storage
  ├── Verifies XBL signature against fused OEM key
  │   └── If fail: halt (brick prevention)
  │
  ▼
XBL (eXtensible Bootloader)
  │
  ├── Initializes DRAM, UFS, display
  ├── Verifies ABL signature against fused OEM key
  │
  ▼
ABL (Android Bootloader — mustang)
  │
  ├── Reads vbmeta_a or vbmeta_b
  │   ├── Extracts AVB descriptor chain
  │   ├── Verifies boot.img hash against vbmeta
  │   └── Verifies system.img root hash against vbmeta
  │
  ├── If user key enrolled:
  │   ├── Replaces OEM verification with user key
  │   └── Verifies all images with user key
  │
  ├── Loads init_boot.img (generic ramdisk)
  ├── Loads vendor_boot.img (vendor ramdisk + DTBO)
  ├── Loads boot.img (kernel + main initramfs)
  │
  ▼
Linux Kernel
  │
  ├── Mounts initramfs from boot.img
  ├── Loads dm-verity target for system partition
  │   ├── Reads root hash from vbmeta (passed via DT/cmdline)
  │   └── Verifies every block read against hash tree
  │
  ├── Mounts system (dm-verity, read-only)
  │   └── If hash mismatch: block not served (I/O error)
  │
  └── switch_root → system userspace
```

### 10.3 AVB Key Management

**Development (unlocked bootloader):**
```
fastboot flash vbmeta_a --disable-verity --disable-verification vbmeta.img
fastboot flash vbmeta_b --disable-verity --disable-verification vbmeta.img
```

**Production (relocked bootloader with user keys):**
```bash
# 1. Generate keys
./tools/gen-keys.sh

# 2. Sign images
./tools/sign-image.sh boot.img
./tools/sign-image.sh system.img

# 3. Create chained vbmeta
avbtool make_vbmeta_image \
    --include_descriptors_from_image boot.img \
    --include_descriptors_from_image system.img \
    --key keys/nuxel-avb.pem \
    --algorithm SHA256_RSA4096 \
    --output vbmeta.img

# 4. Flash signed images + vbmeta
fastboot flash boot boot.img.signed
fastboot flash system system.img.signed
fastboot flash vbmeta vbmeta.img

# 5. Enroll public key in bootloader
fastboot oem avb_set_key keys/nuxel-avb-public.bin

# 6. Relock bootloader
fastboot flashing lock
```

**Relocking is irreversible without the user's key.** Keep backup copies of `keys/` securely.

---

## 11. Audit Logging

All portal accesses and capability grants are logged:

```json
// /var/log/nuxel/audit.log
{
    "timestamp": "2026-05-10T14:31:00Z",
    "event": "capability_access",
    "app_id": "org.nuxel.messages",
    "capability": "sms:send",
    "action": "requested",
    "result": "granted",
    "session_id": "abc-123-def"
}
{
    "timestamp": "2026-05-10T14:32:15Z",
    "event": "portal_access",
    "app_id": "org.example.nav",
    "portal": "location",
    "duration": "once",
    "result": "granted"
}
{
    "timestamp": "2026-05-10T14:33:00Z",
    "event": "capability_revoke",
    "app_id": "org.example.nav",
    "capability": "location:read",
    "initiated_by": "user"
}
```

Users can view their full audit log:
- Settings → Privacy → Permission History
- Filterable by app, capability, date range
- Exportable as JSON for inspection

---

## 12. Security Boundary Summary

```
                    User Data
                        │
                    [Portal Dialog]  ← User consent required
                        │
                    nuxel-portal (trusted daemon)
                        │
              ┌─────────┴──────────┐
              │                    │
    Standard Portals          Nuxel Portals
    (xdg-desktop-portal)      (org.nuxel.Portal)
              │                    │
              └─────────┬──────────┘
                        │
                  D-Bus System Bus
                        │
              ┌─────────┴──────────┐
              │                    │
         System Services      nuxel-bridge
         (ModemManager,       (capability gated)
          NetworkManager,           │
          GeoClue, etc.)         PWAs (isolated)
              │                    │
         [AppArmor profiles]    [5-layer sandbox]
```

- **Red line:** User consent required (portal dialog)
- **Blue line:** Trusted system daemon boundary
- **Green line:** D-Bus mediated access
- **Orange line:** Sandboxed app boundary

---

## 13. References

- [GrapheneOS hardening](https://grapheneos.org/features)
- [Bubblewrap namespace isolation](https://github.com/containers/bubblewrap)
- [seccomp BPF best practices](https://github.com/seccomp/libseccomp)
- [Landlock LSM documentation](https://www.kernel.org/doc/html/latest/userspace-api/landlock.html)
- [AppArmor policy reference](https://gitlab.com/apparmor/apparmor/wikis/Policy_Layout)
- [nftables cgroupv2 matching](https://wiki.nftables.org/wiki-nftables/index.php/Matching_cgroups)
- [AVB (Android Verified Boot)](https://android.googlesource.com/platform/external/avb/)
- [dm-verity documentation](https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/verity.html)
- [Titan M3 technical overview](https://9to5google.com/guides/titan-m3/)
- [Wayland security model](https://wayland.freedesktop.org/docs/html/ch04.html)
- [PipeWire access control](https://docs.pipewire.org/page_access.html)
- [Fedora Silverblue immutable model](https://docs.fedoraproject.org/en-US/fedora-silverblue/)
