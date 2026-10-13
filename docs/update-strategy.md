# Nuxel Update Strategy

This document specifies how Nuxel devices and VMs receive atomic, signed, and
rollback-capable system updates. Nuxel ships two update mechanisms because the
two primary targets have fundamentally different boot ecosystems:

| Target             | Ecosystem        | Update mechanism | Root filesystem    |
|--------------------|------------------|------------------|--------------------|
| Pixel 10 Pro XL (`mustang`) | Alpine / postmarketOS | **RAUC** | Read-only, dm-verity, A/B slots |
| Fedora ARM64 UTM VM (quinn) | Fedora + rpm-ostree | **OSTree** | Read-only `usr`, LVM/plain userdata |

Both mechanisms share the same invariants:

- **A/B (or active/inactive) slot concept** — an update is written to the
  inactive slot while the current slot keeps running; activation happens once
  on the next boot.
- **Rollback-on-boot-failure** — if the newly activated slot fails to boot,
  the bootloader/rollback logic automatically falls back to the previous
  known-good slot.
- **Signed updates** — every bundle/commit is cryptographically signed; the
  platform verifies the signature before applying or activating.
- **Atomic userdata** — user data is carried in a way that is never
  destructively rewritten by an update. On `mustang` this is LUKS2-encrypted
  userdata; on the Fedora VM it is a plain LVM/partition userdata volume.

---

## 1. RAUC for pmOS / mustang

RAUC (Robust Auto-Update Controller) manages atomic updates of embedded Linux
systems. On `mustang` the system runs from a read-only root filesystem built by
postmarketOS and modified by Nuxel. The boot layout uses two slots
(`rootfs.0` / `rootfs.1`) backed by the device's A/B partitions.

### 1.1 Configuration

The RAUC system configuration lives at:

- `images/rauc/mustang-system-bundle.conf` — the on-device `system.conf`
  describing the compatible string, the keyring path, and the slot layout.
- `images/rauc/rauc-config.in` — the bundle manifest template (`RAUC
  bundle` build descriptor) used to assemble a `nuxel-mustang-<ver>.raucb`
  bundle.

The compatible string is pinned to `nuxel-mustang`. A bundle is only accepted
by a device whose `system.conf` compatible string matches the bundle's
`compatible=` manifest entry.

### 1.2 Slot layout

Two independent root filesystems are kept on dedicated partitions:

```
partition: system_a  → RAUC slot  rootfs.0   (active)
partition: system_b  → RAUC slot  rootfs.1   (inactive)
```

RAUC's `bootloader` slot is the boot partition (`boot_a`/`boot_b`) which is
extended so RAUC can persist "last good" status across the bootloader. Boot
status is stored in the bootloader environment and checked on every boot.

```ini
[slot.rootfs.0]
device=/dev/disk/by-partlabel/system_a
type=raw

[slot.rootfs.1]
device=/dev/disk/by-partlabel/system_b
type=raw
```

### 1.3 Signing

Updates are signed with an ED25519 key (or GPG if you prefer asymmetric RSA).
The private key is **never placed on the device**. The public key is embedded
into the device's RAUC keyring (`/etc/rauc/keyring.pem`).

- Keyring path on device: `/etc/rauc/keyring.pem`
- Signing key used to build bundles (host only): `keys/rauc-dev.key.pem`

#### Generating the signing key, certificate and bundle keyring

A typical Nuxel signing setup uses an ED25519 key. In addition to the private
key and certificate, `images/build-ota.sh` looks for a *bundle-embedded public
keyring* at `keys/rauc-public-keyring.pem` (`--keyring` to `rauc bundle`).
Generate all three artifacts as follows:

```sh
mkdir -p keys

# 1. ED25519 private key (kept on the host only, never shipped to the device)
openssl genpkey -algorithm ED25519 -out keys/rauc-dev.key.pem

# 2. Self-signed x509 certificate embedding that public key
openssl req -new -x509 \
    -key  keys/rauc-dev.key.pem \
    -out  keys/rauc-cert.pem \
    -days 7300 \
    -subj "/CN=nuxel-mustang-ota"

# 3. The bundle-embedded public keyring: export the public half of the
#    certificate and concatenate it into keys/rauc-public-keyring.pem so that
#    RAUC can embed a shared verification root inside the .raucb bundle.
openssl x509 -in keys/rauc-cert.pem \
    > keys/rauc-public-keyring.pem

# (Optional) The same cert also seeds the on-device keyring:
#   sudo install -D -m0644 keys/rauc-public-keyring.pem /etc/rauc/keyring.pem
```

> `--signing-keyring` is **not** a valid `rauc bundle` option. The script
> uses the legitimate `--keyring` (bundle-embedded keyring) only when
> `keys/rauc-public-keyring.pem` exists; otherwise it bundles without one and
> logs a warning (a bundle verified with `--cert/--key` still carries a valid
> signature).

### 1.4 Building a bundle

A full bundle contains the root image plus optional artifacts (firmware, boot
image). The bundle workflow:

```sh
# 1. Build a new rootfs image (see images/build.sh / images/mkrootfs.sh)
# 2. Build the bundle with the signing key:

# (using the provided script; example run)
bash images/build-ota.sh --target pmos --version 0.1.1 \
    --rootfs build/out/rootfs.ext4 \
    --boot build/out/boot.img \
    --key keys/rauc-dev.key.pem

# Direct RAUC invocation (equivalent):
rauc bundle \
    --cert keys/rauc-cert.pem \
    --key  keys/rauc-dev.key.pem \
    images/rauc/rauc-config.in \
    build/out/nuxel-mustang-0.1.1.raucb
```

`rauc-config.in` references the generated images via RAUC's `IMG_*`
substitution variables, so the same manifest works for any build:

```ini
[update]
compatible=nuxel-mustang

[bundle]
format=verity

[image.rootfs]
filename=/dev/null   # filled in by images/build-ota.sh from $RAUC_IMG_ROOTFS
```

> Note: `rauc-config.in` is a template. `images/build-ota.sh` expands the
> `@@IMG_ROOTFS@@`, `@@IMG_BOOT@@`, and `@@FILENAME@@` markers to the concrete
> artifact paths before invoking `rauc`. See the script and section 1.5.

### 1.5 Applying on device

```sh
# Transfer the bundle to the device
scp build/out/nuxel-mustang-0.1.1.raucb nuxel@mustang:/tmp/

# Mark the inactive slot as marked-good owner and install
rauc install /tmp/nuxel-mustang-0.1.1.raucb
```

RAUC installs to the inactive slot, verifies the signature, and stages
activation. On the next reboot the bootloader activates the new slot. If the
new slot fails to boot (detected via the bootloader status marker), RAUC
automatically rolls back to the previous slot.

### 1.6 Rollback and status

```sh
rauc status               # show slot states
rauc status mark-good     # mark current slot good (after a successful boot)
rauc status mark-active   # flip active slot
rauc info nuxel-mustang-0.1.1.raucb   # inspect a bundle
```

To manually roll back without rebooting after a failure:

```sh
rauc status mark-active other          # switch to the other slot
rauc status mark-good                  # mark it good
reboot
```

### 1.7 Update notifications & scheduling

The `nuxel-update` service (systemd, `services/nuxel-update`) queries the
update server, downloads bundles, verifies signatures, and triggers
`rauc install`. In the Phosh UI, the "About → System update" PWA surfaces the
same state through the bridge.

---

## 2. OSTree for the Fedora ARM64 VM

The Fedora ARM64 UTM VM (`quinn`) uses rpm-ostree-style image-based updates.
An OSTree commit is a deduplicated, content-addressed snapshot of the entire
`/usr` tree. Booting is atomic: the bootloader selects a deployment, and an
OS update simply adds a new deployment.

### 2.1 Flow overview

```
rpm-ostree compose tree  →  ostree commit  →  GRUB update  →  atomic deploy on the VM
```

1. **Compose** — `rpm-ostree compose tree` turns a `treefile.yaml` (Fedora
   version + a base package set including Nuxel packages) into an OSTree
   repository with a single commit.
2. **Commit** — the composed commit is imported into the VM's OSTree repo.
3. **Bootloader** — GRUB's `grub2-editenv` is updated with the new
   deployment, and on reboot GRUB boots the new deployment.
4. **Atomic deploy** — `rpm-ostree deploy` (or `dnf system-upgrade` /
   `bootc` on newer Fedora) atomically switches `deployments`.

### 2.2 Composing the tree

Create a `treefile.yaml`, e.g. `images/ostree/nuxel-vm-treefile.yaml`:

```yaml
ref: nuxel/fedora/arm64/utm
base:
  - fedora-release
  - kernel
  - systemd
  - NetworkManager
  - phosh
  - ...
include:
  - nuxel-vm-extra.yaml
```

Then:

```sh
rpm-ostree compose tree --repo=/srv/ostree/repo images/ostree/nuxel-vm-treefile.yaml
```

### 2.3 Pushing to the VM

```sh
# On the compose host
mkdir -p /srv/ostree/repo
ostree --repo=/srv/ostree/repo init --mode=archive
rpm-ostree compose tree --repo=/srv/ostree/repo images/ostree/nuxel-vm-treefile.yaml

# Import into the VM's repo (over the bridge or via the shared UTM volume)
ostree --repo=/srv/ostree/repo pull <vm> nuxel/fedora/arm64/utm

# Inside the VM
rpm-ostree deploy nuxel/fedora/arm64/utm@<commit>
systemctl reboot
```

### 2.4 Rollback

rpm-ostree keeps the previous deployment around:

```sh
rpm-ostree rollback          # switch back to the previous deployment
systemctl reboot
```

On boot failure (a `systemd` unit fails to reach a target or the kernel
panics early), the bootloader's built-in logic can fall back to the previous
deployment if `rpm-ostree kargs` / GRUB `saved=` entry is configured. For the
VM, ensure `ostreeadm`-managed GRUB entries exist:

```sh
grub2-editenv /boot/grub2/grubenv set saved_entry=1
```

### 2.5 Userdata on the VM

The VM userdata (home, `/etc`, caches) is stored on a separate plain
LVM/partition volume that is **not** part of the OSTree deployment. An update
never touches it, making userdata updates atomic by construction.

```
LVM VG:   nuxel_vg
  LV nuxel-system   → mounted read-only at /usr  (OSTree deployment)
  LV nuxel-userdata → mounted at /var            (plain, writable)
```

For the VM this is a plain (unencrypted) volume for development; encrypting it
with LUKS2 is optional (`images/initramfs/luks/userdata.crypttab.in` can be
reused if desired).

### 2.6 Signing OSTree commits

OSTree commits are not signed by default; we wrap the compose pipeline in a
GPG signing step:

```sh
ostree --repo=/srv/ostree/repo commit \
    --gpg-sign=<fingerprint> \
    -b nuxel/fedora/arm64/utm
```

The VM verifies with:

```sh
ostree --repo=/ostree/repo remote gpg-import nuxel keys/nuxel-ostree.gpg
rpm-ostree deploy nuxel/fedora/arm64/utm
```

---

## 3. A/B slot concept (both mechanisms)

| Mechanism | Active slot | Inactive slot | Activation trigger        | Rollback trigger                 |
|-----------|-------------|---------------|---------------------------|----------------------------------|
| RAUC      | `rootfs.0`  | `rootfs.1`    | Reboot (bootloader env)   | Boot failure detected by bootloader status marker |
| OSTree    | deployment N-1 | deployment N | `rpm-ostree deploy` + reboot | `rpm-ostree rollback` / GRUB saved entry fallback |

Common guarantees:

- The running system is never modified in place for the OS image.
- Updates are staged in a separate location and applied atomically.
- Signature verification happens **before** a new slot/deployment is marked
  active.

---

## 4. Update server & delivery (shared)

A simple update server (HTTP) is deployed at `https://updates.nuxel.dev/` for
signed artifacts:

| Path                                          | Mechanism | Format                |
|-----------------------------------------------|-----------|-----------------------|
| `/v1/mustang/nuxel-mustang-<ver>.raucb`       | RAUC      | RAUC bundle           |
| `/v1/vm/nuxel/fedora/arm64/utm/`              | OSTree    | OSTree repo (archive) |

The `nuxel-update` service downloads a metadata manifest
(`update.json`) that lists the latest version, its bundle/commit, and the
signature. The metadata file itself is also signed and verified before any
artifact is fetched.

`update.json` example:

```json
{
  "product": "nuxel",
  "version": "0.1.1",
  "target": "mustang",
  "mechanism": "rauc",
  "bundle": "/v1/mustang/nuxel-mustang-0.1.1.raucb",
  "checksum_sha256": "...",
  "signature": "..."
}
```

---

## 5. End-to-end update flow (mustang, production)

1. Nuxel build server produces `nuxel-mustang-<ver>.raucb` (section 1.4),
   signs it, and uploads it plus `update.json` to the update server.
2. `nuxel-update` on the device polls `update.json`, verifies the metadata
   signature and `checksum_sha256`.
3. Bundle is downloaded, RAUC verifies the bundle signature against the
   on-device keyring, and writes it to the inactive slot.
4. On the next reboot the bootloader activates the new slot. The rkt state
   writes `mark-good` after a successful boot (e.g. from `nuxel-update`'s
   oneshot unit or a `rauc.service` run at boot).
5. If the slot doesn't boot, RAUC marks it bad and falls back to the previous
   good slot automatically.

---

## Related documents

- `docs/security-model.md` — dm-verity, AVB, hardened_malloc and the full
  security model.
- `docs/roadmap.md` — the roadmap's OTA section that references this strategy.
- `images/build-ota.sh` — the wrapper that produces update bundles/commits.
- `images/rauc/mustang-system-bundle.conf` — the on-device RAUC `system.conf`.
- `images/ostree/README.md` — the detailed OSTree flow for the Fedora VM.
