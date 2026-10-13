# Archived init files (briq-21)

This directory holds init files that are **non-applicable to a given target**
so they can be preserved without affecting any live boot.

Nuxel has two mutually-exclusive init stacks (see `docs/init-system.md`):

- `[vm]` — Fedora/UTM VM → **systemd**
- `[mustang]` — Alpine/pmOS mustang → **OpenRC**

A `[vm]` (systemd) unit is non-applicable on `[mustang]`, and a `[mustang]`
(OpenRC) script is non-applicable on `[vm]`. Every init file in the tree
currently applies to exactly one target, so the live set is never empty and
no file has been moved here yet. If a service is later dropped from one
target but kept in the other, its init file should be moved into this
directory (with a short note) instead of deleted.

## Categorization matrix

| File                                                | Category   | Live on       |
|-----------------------------------------------------|------------|---------------|
| `services/nuxel-bridge/systemd/nuxel-bridge.service`        | `[vm]`   | systemd (VM) |
| `services/nuxel-bridge/systemd/nuxel-http-bridge.service`   | `[vm]`   | systemd (VM) |
| `services/nuxel-portal/systemd/nuxel-portal.service`        | `[vm]`   | systemd (VM) |
| `services/nuxel-notifications/systemd/nuxel-notifications.service` | `[vm]` | systemd (VM) |
| `services/nuxel-web.service`                                 | `[vm]`   | systemd (VM) |
| `shell/config/systemd-user/nuxel-phosh-agent.service`        | `[vm]`   | systemd (VM) |
| `shell/config/systemd-user/nuxel-home-kiosk.service`         | `[vm]`   | systemd (VM) |
| `shell/config/systemd-user/nuxel-home-native.service`        | `[vm]`   | systemd (VM) |
| `configs/apparmor/systemd/nuxel-apparmor-enforce.service`    | `[vm]`   | systemd (VM) |
| `shell/config/openrc/nuxel-bridge`       | `[mustang]` | OpenRC (mustang) |
| `shell/config/openrc/nuxel-portal`       | `[mustang]` | OpenRC (mustang) |
| `shell/config/openrc/nuxel-notifications`| `[mustang]` | OpenRC (mustang) |
| `shell/config/openrc/nuxel-firstboot`    | `[mustang]` | OpenRC (mustang) |
