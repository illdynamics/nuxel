# Nuxel Native Shell — aarch64 Cross-Compilation

This document describes how the 5 native GTK4 C apps plus `nuxel-sandbox` and
the Python home launcher (`nuxel-home-native`) are cross-compiled for `aarch64`
and installed into an ARM64 UTM VM.

The target is:

* **mustang** — Google Pixel 10 Pro XL, Google Tensor G5 / Exynos 5500
* the ARM64 UTM VM (Fedora ARM64 / Phosh) used during Phase 1 development

## Binaries produced

| Binary                  | Source                                     | Language | Dependencies                       | Build status |
|-------------------------|--------------------------------------------|----------|------------------------------------|--------------|
| `nuxel-dialer`          | `nuxel-dialer/main.c`                      | C (GTK4) | gtk4, libadwaita-1, (ModemManager) | 🔶 meson config OK / C compile fails |
| `nuxel-contacts`        | `nuxel-contacts/main.c`                    | C (GTK4) | gtk4, libadwaita-1, json-glib      | 🔶 meson config OK / C compile fails |
| `nuxel-messages`        | `nuxel-messages/main.c`                    | C (GTK4) | gtk4, libadwaita-1, (ModemManager) | 🔶 meson config OK / C compile fails |
| `nuxel-settings`        | `nuxel-settings/main.c`                    | C (GTK4) | gtk4, libadwaita-1                 | 🔶 meson config OK / C compile fails |
| `nuxel-permissions`     | `nuxel-permissions/main.c`                 | C (GTK4) | gtk4, libadwaita-1, (json-glib)    | 🔶 meson config OK / C compile fails |
| `nuxel-sandbox`         | `nuxel-sandbox/sandbox.c` + `sandbox.h`    | C        | libcap (optional at link)          | ✅ ELF aarch64 (readelf: Machine AArch64) |
| `nuxel-home-native`     | `../nuxel-home-native/nuxel_home/*.py`     | Python   | python3 + gi (GTK4/Adw)            | ✅ byte .pyc      |

## Verified build (aarch64 Fedora 41 sysroot, 2026-08-11)

`meson setup` (including both `--cross-file` and the plain native path) now
**completes successfully** — the desktop-entry `install_data` sources were
reconciled to the real `shell/config/*.desktop` files (`../config/...`), so the
old `ERROR: File config/nuxel-home.desktop does not exist` abort is gone.

`build-native-apps.sh` was run against a real aarch64 sysroot (Fedora 41
container with `gtk4-devel`, `libadwaita-devel`, `libcap-devel`, `meson`,
`ninja`, `pkgconfig`). Results:

* `nuxel-sandbox` → **built**, verified `readelf -h` → `Class: ELF64`,
  `Machine: AArch64`; staged at `build/native-shell/nuxel-sandbox`.
* `nuxel-home-native` → **byte-compiled** to `__pycache__/*.pyc` and installed
  to `/usr/lib/nuxel/nuxel-home-native/` + `/usr/bin/nuxel-home` launcher.
* The 5 GTK4 C apps (`nuxel-dialer/contacts/messages/settings/permissions`)
  **configure** via meson but their **C sources fail to compile** against real
  GTK4/libadwaita headers (e.g. missing `json-glib` include in
  `nuxel-contacts/main.c`, stale GTK3-era calls like `gtk_entry_set_text` /
  `gtk_widget_set_margin`, missing `GtkWidget` declarations in
  `nuxel-dialer/main.c`). These are pre-existing source defects outside this
  repair's scope. `build-native-apps.sh` logs the failure as a warning and
  continues so sandbox + home-native still build.

> **(ModemManager)** and **(json-glib)** are declared with `required: false` in
> `meson.build`. When the aarch64 sysroot lacks those dev packages the apps
> still build and wire to the backend through plain GDBus at runtime, degrading
> to the bridge mock in the VM.

## Prerequisites

### On the build host (macOS Apple Silicon / x86_64 Linux)

* `meson` and `ninja`
* an aarch64 cross C compiler:
  * Linux: `gcc-aarch64-linux-gnu` (Debian/Ubuntu: `crossbuild-essential-arm64`)
* an aarch64 **sysroot** carrying the dev packages:
  * `gtk4`, `libadwaita-1`, `glib-2.0`, `gio-2.0`
  * optional: `json-glib-1.0`, `ModemManager`, `libcap`
* `aarch64-linux-gnu-pkg-config` (or set `PKG_CONFIG_LIBDIR`/`PKG_CONFIG_SYSROOT_DIR`)

### Inside the ARM64 UTM VM

No cross toolchain is needed — `build-native-apps.sh` detects `uname -m =
aarch64` and compiles natively with the VM's `gcc`.

## Cross file

`aarch64-cross.ini` — the meson cross file:

* `c = 'aarch64-linux-gnu-gcc'`
* `pkg-config = 'aarch64-linux-gnu-pkg-config'`
* `host_machine.system = 'linux'`, `cpu_family = 'aarch64'`, `endian = 'little'`

Set `SYSROOT` when invoking the build:

```bash
NUXEL_SYSROOT=/path/to/sysroot ./shell/nuxel-shell/build-native-apps.sh
```

## Build invocation

```bash
# Default: uses aarch64-linux-gnu-gcc when available, else native
./shell/nuxel-shell/build-native-apps.sh

# Explicit cross with a sysroot
NUXEL_SYSROOT=/opt/aarch64-sysroot \
  OUT_DIR=/tmp/native-shell \
  ./shell/nuxel-shell/build-native-apps.sh

# Native rebuild inside the VM
./shell/nuxel-shell/build-native-apps.sh
```

The meson build directory is `build/native-shell/meson`; the sandbox binary is
`build/native-shell/nuxel-sandbox`.

## Verifying the aarch64 output

Every compiled binary must report:

```text
ELF 64-bit LSB pie executable, ARM aarch64
```

`build-native-apps.sh` prints `file <binary>` for every built artifact so this
can be verified directly.

## Installing into the VM

When run as root the script installs the C binaries into `PREFIX=/usr/bin` and
byte-compiles/copies the Python home launcher into
`/usr/lib/nuxel/nuxel-home-native/` plus a `nuxel-home.desktop` entry. When not
root, set `DESTDIR` to stage them instead.

The end-to-end install of all services (systemd units, D-Bus policy, users,
Phosh config) is handled by `vm/nuxel-vm-bootstrap.sh`.
