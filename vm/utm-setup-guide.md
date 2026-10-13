# Nuxel UTM VM Setup Guide

## Purpose

This guide walks through creating a **Nuxel development VM** on an Apple Silicon
MacBook (M1/M2/M3/M4) using **UTM** — a free, open-source macOS GUI for QEMU
virtual machines. The VM runs a hardened ARM64 Linux OS with **Phosh** as the
mobile shell, reproducing the Nuxel phone OS environment for development and
testing before physical hardware deployment (Pixel 10 Pro XL "mustang").

---

## Prerequisites

- **Apple Silicon Mac** (M1, M2, M3, or M4) — Intel Macs can follow along but
  will run ARM64 under emulation (slower).
- **macOS 13+** (Ventura or later)
- **At least 20 GB free disk space** for VM image + guest OS
- **Optional but recommended:** 8 GB+ RAM free for the VM

---

## Step 1: Install UTM

1. Download UTM from the official site: <https://mac.getutm.app/>
2. Or install via Homebrew:
   ```bash
   brew install --cask utm
   ```
3. Launch UTM. You should see the main "UTM Virtual Machines" window.

> **Why UTM?** UTM uses Apple's native Hypervisor.framework on Apple Silicon,
> giving ARM64 Linux VMs near-native CPU performance. This is critical for
> testing Phosh/GTK4 performance, app sandbox isolation, and portal behavior
> at phone-like resolutions without needing physical Pixel hardware.

---

## Step 2: Create a New ARM64 VM

1. Click **"Create a New Virtual Machine"** (the `+` icon or **File → New**).
2. Select **"Virtualize"**.
3. Choose **"Linux"** as the operating system.
4. Under **"Boot ISO Image"**, click **"Browse"** and select a Nuxel installer ISO
   or a base distro ISO (see *Step 3* for distro choices).

### VM Hardware Settings

Set these values in the UTM VM configuration:

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Architecture** | `aarch64` (ARM64) | Matches Pixel 10 Pro XL (mustang) CPU family |
| **System** | `ARM64 virt` (QEMU `virt` machine) | Best ARM64 VM support |
| **CPU cores** | `4` | Mimics modern phone SoC big.LITTLE cluster count |
| **RAM** | `4096–8192 MB` (4–8 GB) | Pixel 10 Pro XL has 16 GB; 4–8 GB suffices for dev |
| **Display** | `virtio-gpu` or `virtio-gpu-gl` | Hardware-accelerated GPU in VM |
| **Disk** | `40–80 GB` (sparse/qcow2) | System + apps + test data |

### Networking Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Mode** | `Shared (NAT)` | Guest uses host internet; no extra config needed |
| **Network card** | `virtio-net` | Paravirtualized, high-performance |

### Security Testing Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Shared folders** | `Disabled` | Prevents host→guest filesystem leakage during sandbox testing |
| **Clipboard sync** | `Disabled` | Prevents clipboard data leaks between host/guest |
| **USB passthrough** | `Disabled initially` | Enable only when testing USB portal functionality |
| **Audio** | `Enabled (virtio-sound)` | Test PipeWire/Wayland audio path |

---

## Step 3: Choose a Guest Distribution

### Option A: Fedora ARM64 (Recommended for first-time setup)

```text
Download: https://dl.fedoraproject.org/pub/fedora/linux/releases/41/Spins/aarch64/iso/
Look for: Fedora-Phosh-Live-aarch64-*.iso
```

Fedora offers an official **Phosh spin** for ARM64, which saves significant
setup time. The Phosh spin includes:

- phosh shell
- phoc compositor (wlroots-based Wayland compositor)
- squeekboard (on-screen keyboard)
- calls (Phone dialer)
- chatty (SMS/MMS)
- GNOME Settings (mobile-friendly)

### Option B: Debian ARM64 (For maximum compatibility testing)

```text
Download: https://cdimage.debian.org/debian-cd/current/arm64/iso-cd/
```

Debian requires manual Phosh installation but is closer to the distro base
that Nuxel targets for its service stack.

### Option C: Nuxel Builder ISO (Once available)

The build tooling in `tools/nuxel-build.sh` produces a combined bootable ISO.
Use this ISO directly in UTM once it's generating Nuxel-specific images.

---

## Step 4: Install the Guest OS

1. In UTM's VM window, click **"Start"**.
2. The VM will boot from the ISO you attached.
3. Follow the distro's installer:
   - **Fedora Phosh:** The live environment boots directly into Phosh. Use the
     "Install to Hard Disk" icon.
   - **Debian:** Use the standard text/graphical installer.
4. Partitioning: Use guided partitioning with LVM or ext4 on a single root
   partition. Nuxel's immutable image model will layer on top in later phases.
5. Create a user account during installation (this will become the "nuxel" user
   on the hardened profile).

> **Important:** If your VM boots to a blank screen after install, add
> `video=800x1280` or similar to the kernel cmdline in the UTM boot options.

---

## Step 5: Configure Phone-Shaped Resolution

Run the **`phosh-phone-resolution.sh`** script (included in the Nuxel `vm/`
directory) inside the VM to force a mobile-phone aspect ratio:

```bash
# Inside the VM
sudo ./vm/phosh-phone-resolution.sh 390x844
```

The script supports these presets:

| Preset | Resolution | Aspect Ratio | Use Case |
|--------|-----------|--------------|----------|
| `390x844` | 390 × 844 | ~1:2.16 | iPhone-style compact phone |
| `414x896` | 414 × 896 | ~1:2.16 | Standard phone (iPhone Plus) |
| `720x1280` | 720 × 1280 | 9:16 | HD phone portrait (Android standard) |

The script:
- Creates a Wayland display configuration at the chosen resolution
- Configures Phosh to use phone-layout (`phosh-lockdown-mode=on`)
- Restarts the Phosh session
- Enables the on-screen keyboard and notch/cutout demo mode

---

## Step 6: Install Nuxel Core Services

Run the bootstrap script to install all Nuxel OS services:

```bash
# Inside the VM
sudo ./vm/nuxel-vm-bootstrap.sh
```

The script installs and configures:

| Component | Service | Purpose |
|-----------|---------|---------|
| **nuxel-bridge** | `nuxel-bridge.service` | D-Bus permission broker |
| **nuxel-portal** | `nuxel-portal.service` | Hardware access consent dialogs |
| **nuxel-notifications** | `nuxel-notifications.service` | On-device notification hub |
| **nuxel-firstboot** | `nuxel-firstboot.service` | First-boot setup wizard |
| **nuxel-sandbox** | — | Sandbox launcher (bubblewrap + namespaces) |
| **AppArmor** | `apparmor.service` | Mandatory access control |
| **nftables** | `nftables.service` | Per-app network rules |
| **hardened_malloc** | `libhardened_malloc.so` | Heap hardening via LD_PRELOAD |

### Step 6.5: Build the bootable VM disk image (recommended path)

Instead of hand-installing, you can produce a **verified, bootable ARM64 disk
image** from a base Fedora/Debian qcow2 in one step. On the Apple Silicon host:

```bash
# 1. Ensure qemu tooling (for qemu-img creation/conversion + virtual sizes)
brew install qemu

# 2. Point at a base ARM64 disk and build
VM_DISK_IMAGE=/path/to/Fedora-Cloud-Base-41-1.4.aarch64.qcow2 \
  ./vm/build-vm-image.sh

# 3. Or auto-download a base image
VM_IMAGE_URL=https://dl.fedoraproject.org/pub/fedora/linux/releases/41/Cloud/aarch64/images/Fedora-Cloud-Base-41-1.4.aarch64.qcow2 \
  ./vm/build-vm-image.sh
```

This produces:

```
artifacts/vm/nuxel-aarch64.utm                <- UTM bundle (open/boot in UTM)
artifacts/vm/nuxel-aarch64.qcow2              <- standalone bootable disk
artifacts/vm/nuxel-aarch64.img                <- raw image (when converted)
```

The builder **verifies the disk** at the end (non-empty, qcow2 magic `QFI\xfb`,
raw-ext/btrfs magic when applicable). To verify an existing artifact on any host:

```bash
./ci/phase3-smoke-vm.sh --image artifacts/vm/nuxel-aarch64.qcow2
```

Documented expected output (pass):

```
--- Bootable VM Image Assertion (briq-v2) ---
  [✓] image non-empty (6885777408 bytes): artifacts/vm/nuxel-aarch64.qcow2
  [✓] qcow2 magic (QFIû) detected
  [✓] qemu-img confirms qcow2 format
  [✓] IMAGE VERIFICATION PASSED: artifacts/vm/nuxel-aarch64.qcow2
  Expected when booting (UTM host): VM boots to Phosh at 720x1440
```

A garbage/empty disk yields `[✗] IMAGE VERIFICATION FAILED ...` and exit code 1.

To boot the image headlessly and run the bootstrap automatically, on the UTM host:

```bash
# Boot the bundle, wait for ssh, run bootstrap, then shutdown cleanly:
./vm/build-vm-image.sh                      # (do NOT set SKIP_BOOT)

# Or stage only (no boot) for a later manual boot:
SKIP_BOOT=1 ./vm/build-vm-image.sh

# Boot/stop an already-built VM with utmctl:
utmctl start nuxel-aarch64.utm
utmctl stop  nuxel-aarch64.utm
utmctl list

# If you built the bundle manually, attach the disk in UTM GUI
# (Drives -> disk-0.qcow2) and click Start.
```

> **Boot requirement:** full VirtIO GUI boot to a Phosh session requires the
> Apple Silicon UTM host (UTM is a macOS GUI app backed by Hypervisor.framework).
> In a headless CI sandbox, `build-vm-image.sh` still stages + verifies the disk,
> and `phase3-smoke-vm.sh --image …` asserts it is bootable without booting.

### Step 6.6: First-boot marker

The bootstrap creates the first-boot marker parent directory `/var/lib/nuxel/`
and a `.pending-firstboot` sentinel there. The `nuxel-firstboot` service moves
it to the canonical `/var/lib/nuxel/.firstboot-complete` on its first graphical
run. Verify the parent dir exists after bootstrap:

```bash
sudo ls -la /var/lib/nuxel/            # expect .pending-firstboot present
```

---

## Step 7: Verify the Environment

After reboot, verify each component:

```bash
# Check Wayland session
echo $WAYLAND_DISPLAY
# Should output: wayland-0

# Check Phosh is running
ps aux | grep phosh

# Check portal daemon responds to Ping (briq-v1)
gdbus call --system --dest org.nuxel.Portal \
  --object-path /org/nuxel/Portal --method org.nuxel.Portal.Ping smoke
# Expected reply: ('{"pong": "smoke", ...}',)

# All Nuxel systemd units must be active (running)
systemctl is-active nuxel-bridge.service nuxel-portal.service \
  nuxel-notifications.service nuxel-http-bridge.service nuxel-web.service
# Expected: printed once per unit, all 'active'

# Check AppArmor
sudo aa-status

# Check nftables rules
sudo nft list ruleset

# Check resolution
wlr-randr

# Full runtime smoke (PWA -> HTTP API -> bridge -> portal -> PhoshAgent)
# Must be run INSIDE the running VM:
./ci/phase3-smoke-vm.sh
```

---

## Step 8: Take a Snapshot (Save State)

From the **UTM main window**, select your VM and pause it. Use **File → Save
State** or **Manage → Snapshot** to create a snapshot before security testing,
kernel experiments, or update rollback tests.

For CLI-based snapshot management, use the included `vm/nuxel-vm-snapshot.sh`
script.

---

## Troubleshooting

### VM boots to black screen

- Ensure `virtio-gpu` or `virtio-gpu-gl` is selected as the display.
- Add `nomodeset` to the kernel command line for fallback framebuffer.
- Try `video=720x1280` in kernel cmdline.

### Phosh doesn't start

- Check `.bash_profile` / `.xinit` for display manager settings.
- Ensure `phoc` has the right WLROOTS_CONFIG.
- Re-run `./vm/phosh-phone-resolution.sh`.

### Permissions not working

- Verify `nuxel-bridge` and `nuxel-portal` services are running:
  ```bash
  sudo systemctl status nuxel-bridge nuxel-portal
  ```
- Check `/var/lib/nuxel/permissions/` for permission files.
- Check AppArmor profiles in `/etc/apparmor.d/nuxel-*`.

### No network in VM

- Ensure UTM is set to **Shared (NAT)** mode.
- In the guest: `sudo dhclient eth0` or `sudo systemctl restart NetworkManager`.

### Clipboard still sharing in isolation test

- Go to UTM VM settings → **Sharing** → uncheck **Clipboard sharing**.
- Restart the VM.

### Bootstrap does not reach exit 0

The bootstrap is deterministic and idempotent; a mid-run abort is almost always
a missing dependency or a transient network failure during `dnf/apt install`.
Workarounds:

- Retry: `sudo ./vm/nuxel-vm-bootstrap.sh` — re-running is safe (user/dirs already
  exist are skipped).
- Check the exact failing step from the `[INFO]/[WARN]/[ERROR]` banner, then run
  that step's package install manually and re-run.
- If `useradd` complains about a missing group (`adb`/`docker`), the script now
  skips nonexistent groups automatically.

### First-boot marker is missing

The bootstrap creates `/var/lib/nuxel/.pending-firstboot`. If it is not present
after a successful bootstrap, run:

```bash
sudo mkdir -p /var/lib/nuxel && sudo touch /var/lib/nuxel/.pending-firstboot
```

The `nuxel-firstboot` service flips it to `/var/lib/nuxel/.firstboot-complete`.

### Image assertion shows `no filesystem magic found`

The staged disk is a scaffold, not a bootable OS. Rebuild with a real base image:

```bash
VM_DISK_IMAGE=/path/to/arm64.qcow2 ./vm/build-vm-image.sh
```

### utmctl says "not found"

`utmctl` ships with UTM CLI (brew). Use the GUI instead: open
`artifacts/vm/nuxel-aarch64.utm` in UTM and press **Start**, or run
`open artifacts/vm/nuxel-aarch64.utm`.

---

## References

- UTM documentation: <https://docs.getutm.app/>
- Phosh project: <https://phosh.mobi/>
- Fedora Phosh: <https://fedoraproject.org/spins/phosh/>
- QEMU ARM64 virt machine: <https://www.qemu.org/docs/master/system/arm/virt.html>
- Nuxel design doc: `nuxel-linux-phone-design.md`
- Nuxel milestone tracking: `docs/milestones.md`
