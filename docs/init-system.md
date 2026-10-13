# Nuxel Init System Split (briq-21)

Nuxel ships two different init/service-management stacks depending on the
target platform. They are kept separate and never mixed. This document
defines the split, how the build chooses between them, and what happens to
init files that do not apply to a given target.

## Targets

### `[vm]` — Fedora / UTM VM (systemd)

The development and validation target is an ARM64 Fedora UTM VM running
Phosh. It uses **systemd** for system services and **systemd user services**
for the session shell/agent stack.

- System services: `services/nuxel-bridge/systemd/*.service`,
  `services/nuxel-portal/systemd/*.service`,
  `services/nuxel-notifications/systemd/*.service`,
  `services/nuxel-web.service`
- User services: `shell/config/systemd-user/*.service`
  (`nuxel-phosh-agent.service`, `nuxel-home-kiosk.service`,
  `nuxel-home-native.service`)
- The VM rootfs builder (`images/mkrootfs.sh`) and the VM bootstrap
  (`vm/nuxel-vm-bootstrap.sh`) operate with `NUXEL_INIT=systemd`.

Targets: `UTM VM (Fedora/Phosh) -> systemd`.

### `[mustang]` — Alpine / pmOS (OpenRC)

The physical phone target (Google Pixel 10 Pro XL "mustang", running Alpine /
postmarketOS) uses **OpenRC** (`/sbin/openrc-run` scripts).

- OpenRC init scripts: `shell/config/openrc/*`
  (`nuxel-bridge`, `nuxel-portal`, `nuxel-notifications`, `nuxel-firstboot`)
- These are openrc-run style scripts using `start-stop-daemon` and
  `checkpath`, with `depend()` blocks wired to the Alpine/pmOS boot scripts
  (`dbus`, `base`, `localmount`, `modloop`, `network`).

Targets: `mustang (Alpine/pmOS) -> OpenRC`.

## NUXEL_INIT selection

The build/bootstrap detects the init system and stores it in the `NUXEL_INIT`
environment variable:

- `NUXEL_INIT=systemd` → Fedora/UVM VM (install systemd units, D-Bus
  policies, multi-user.target.wants).
- `NUXEL_INIT=openrc` → mustang/Alpine-pmOS (install OpenRC scripts into
  `/etc/init.d/`, enable via `rc-update add ... boot`).

Each bootstrap script sets a sensible default for its platform but honors an
explicit override:

```sh
# vm/nuxel-vm-bootstrap.sh (default systemd for the Fedora/UVM VM):
export NUXEL_INIT="${NUXEL_INIT:-systemd}"
# images/mkrootfs.sh — set NUXEL_INIT=openrc to produce an OpenRC rootfs for the
# mustang/Alpine-pmOS target (installs shell/config/openrc/*, codes them into the boot runlevel):
export NUXEL_INIT="${NUXEL_INIT:-openrc}"
```

When neither systemd nor OpenRC is detected at runtime, the bootstrap falls
back to the target default above.

## D-Bus policy configuration

All D-Bus system policies live in the single combined directory
`configs/dbus/` (canonical), and are installed by both init paths:

- `configs/dbus/org.nuxel.Bridge.conf`
- `configs/dbus/org.nuxel.Portal.conf`
- `configs/dbus/org.nuxel.Notifications.conf`

The per-service copies under `services/*/dbus/` are kept as legacy sources for
tooling that predates the combined directory; new installs must prefer
`configs/dbus/`.

## Archived / non-applicable init files

`configs/init/archived/` holds init files that are non-applicable to their
target. The categorization rules:

- Every `[vm]` (systemd) unit is non-applicable on `[mustang]`.
- Every `[mustang]` (OpenRC) script is non-applicable on `[vm]`.

Because the two stacks are mutually exclusive, the "live" set for a given
target is exactly the files for that target; the files for the *other* target
are considered archived *with respect to the current build*. The
`configs/init/archived/` directory documents this matrix:

| File                                          | Category   | Live on      |
|-----------------------------------------------|------------|--------------|
| `services/nuxel-bridge/systemd/nuxel-bridge.service`          | `[vm]`   | systemd (VM) |
| `services/nuxel-bridge/systemd/nuxel-http-bridge.service`     | `[vm]`   | systemd (VM) |
| `services/nuxel-portal/systemd/nuxel-portal.service`          | `[vm]`   | systemd (VM) |
| `services/nuxel-notifications/systemd/nuxel-notifications.service` | `[vm]` | systemd (VM) |
| `services/nuxel-web.service`                                   | `[vm]`   | systemd (VM) |
| `shell/config/systemd-user/nuxel-phosh-agent.service`          | `[vm]`   | systemd (VM) |
| `shell/config/systemd-user/nuxel-home-kiosk.service`           | `[vm]`   | systemd (VM) |
| `shell/config/systemd-user/nuxel-home-native.service`          | `[vm]`   | systemd (VM) |
| `configs/apparmor/systemd/nuxel-apparmor-enforce.service`      | `[vm]`   | systemd (VM) |
| `shell/config/openrc/nuxel-bridge`         | `[mustang]` | OpenRC (mustang) |
| `shell/config/openrc/nuxel-portal`         | `[mustang]` | OpenRC (mustang) |
| `shell/config/openrc/nuxel-notifications`  | `[mustang]` | OpenRC (mustang) |
| `shell/config/openrc/nuxel-firstboot`      | `[mustang]` | OpenRC (mustang) |

At present every init file in the tree applies to exactly one target, so the
working set is never empty; nothing is orphaned. The `archived/` directory
exists so that if a service is later dropped from one target (but kept in the
other), its init file can be moved there instead of being deleted, preserving
the history without affecting the live boot.
