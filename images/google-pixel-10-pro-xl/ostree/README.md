# OSTree / rpm-ostree update flow for the Fedora ARM64 VM

This directory documents the image-based update flow for the Fedora ARM64 UTM
VM (`quinn`). Nuxel uses **OSTree** for the VM and **RAUC** for the
`mustang` phone. See `docs/update-strategy.md` for the comparison and the
rationale.

## Why OSTree for the VM

- The VM bootstraps from Fedora ARM64 (`vm/nuxel-vm-bootstrap.sh`).
- Fedora ships `rpm-ostree`, so image-based updates are the native mechanism.
- Userdata stays on a separate plain LVM/partition volume, making it immune to
  OS updates by construction.

## The flow

```
                       ┌──────────────────────────────┐
                       │       Compose host           │
                       │  rpm-ostree compose tree     │
                       │       (treefile.yaml)        │
                       └──────────────┬───────────────┘
                                      │ import commit
                                      ▼
                       ┌──────────────────────────────┐
                       │   OSTree repo (archive)      │
                       │   /srv/ostree/repo           │
                       └──────────────┬───────────────┘
                                      │ pull over bridge / shared volume
                                      ▼
    ┌─────────────────────────────────────────────────────────┐
    │              Fedora ARM64 VM (quinn)                    │
    │   rpm-ostree deploy nuxel/fedora/arm64/utm@<commit>     │
    │   grub2-editenv / bootloader swaps deployment           │
    │   systemctl reboot  → atomic activation                 │
    └─────────────────────────────────────────────────────────┘
```

### Step 1 — Compose the tree

`rpm-ostree compose tree` turns a `treefile.yaml` into an OSTree repository
containing a single commit that represents the entire `/usr` of the target.

Create `images/ostree/nuxel-vm-treefile.yaml`:

```yaml
ref: nuxel/fedora/arm64/utm
document: fedora.org/image/v1
releasever: "41"
rojig:
  name: nuxel-vm
  summary: Nuxel Fedora ARM64 UTM VM image
  license: MIT
repos:
  - fedora
  - updates

packages:
  - kernel
  - systemd
  - NetworkManager
  - phosh
  - tinydm
  - pipewire
  - pipewire-pulse
  - wireplumber
  # Nuxel native services
  - nuxel-bridge
  - nuxel-portal
  - nuxel-notifications

# Don't include bash-doc etc. — keep the image lean.
default-packages:
  - fedora-release
  - bash
  - coreutils
  - procps-ng
  - util-linux

# Nuxel userdata is a separate LV; keep /usr read-only.
# (OSTree mounts /usr read-only automatically.)
```

Compose:

```sh
sudo dnf install -y rpm-ostree
sudo mkdir -p /srv/ostree/repo
sudo ostree --repo=/srv/ostree/repo init --mode=archive
sudo rpm-ostree compose tree --repo=/srv/ostree/repo \
    images/ostree/nuxel-vm-treefile.yaml
```

List the composed commit:

```sh
sudo ostree --repo=/srv/ostree/repo log nuxel/fedora/arm64/utm | head -10
```

### Step 2 — Commit to the VM's repo

On the VM, pull the composed ref:

```sh
# The VM and compose host share the UTM shared directory or talk over the Nuxel bridge.
sudo ostree --repo=/ostree/repo pull \
    file:///mnt/shared/ostree/repo nuxel/fedora/arm64/utm
```

### Step 3 — Deploy (atomic activation)

```sh
sudo rpm-ostree deploy nuxel/fedora/arm64/utm@<full_commit_hash>
sudo systemctl reboot
```

`rpm-ostree deploy` creates a new deployment without touching the running
one. On reboot GRUB selects the new deployment. If anything is wrong you can
switch back with `rpm-ostree rollback`.

### Step 4 — Rollback on failure

```sh
# After a bad boot, boot into GRUB and pick the previous entry, OR:
rpm-ostree rollback
sudo systemctl reboot
```

To make fallback automatic, ensure GRUB is OSTree-managed. For a VM using the
OSTree GRUB module this is configured during firstboot. As a safety net, keep
a copy of the previous deployment (rpm-ostree keeps at least the last two by
default):

```sh
rpm-ostree status          # list deployments
sudo rpm-ostree cleanup -p # prune old, keep the previous for rollback
```

## Slot concept in OSTree

OSTree does not use classic A/B partitions. Instead it keeps **multiple
deployments** on the same disk, each a self-contained `/usr` snapshot:

| Concept                     | OSTree equivalent                              |
|-----------------------------|------------------------------------------------|
| A/B slots                   | Deployment N-1 (previous) / Deployment N (new) |
| Activation trigger          | `rpm-ostree deploy` + reboot                   |
| Rollback trigger            | `rpm-ostree rollback` / GRUB saved entry       |
| Signed updates              | GPG-signed commits (optional but recommended)  |
| Atomic userdata             | `/var` on a separate LVM/partition volume      |

## Signing commits

OSTree commits are not signed by default. Nuxel signs them with GPG:

```sh
sudo ostree --repo=/srv/ostree/repo commit \
    --gpg-sign="NUXEL OSTREE 0xFF11..." \
    -b nuxel/fedora/arm64/utm
```

On the VM, import and verify:

```sh
sudo ostree --repo=/ostree/repo remote gpg-import \
    nuxel keys/nuxel-ostree.gpg
sudo rpm-ostree deploy nuxel/fedora/arm64/utm
```

## Userdata volume (VM)

The VM keeps `/var` (and thus user data, `/etc`, caches, home) on a separate
plain LVM/partition volume that is **not** inside the composed tree:

```
LVM VG:  nuxel_vg
  LV nuxel-system   → mounted read-only at /usr    (OSTree)
  LV nuxel-userdata → mounted at /var              (plain, writable)
```

Updates never rewrite `/var`. For the VM this is intentionally unencrypted for
development convenience. If LUKS2 encryption is desired, reuse
`images/initramfs/luks/userdata.crypttab.in` plus `images/hooks/luks-userdata.sh`.

## Related files

- `docs/update-strategy.md` — the overall policy and RAUC/OSTree comparison.
- `images/build-ota.sh` — `--target fedora` builds/pushes an OSTree commit.
- `../build.sh` / `../../images/mkrootfs.sh` — rootfs + image building.
