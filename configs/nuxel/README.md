# Nuxel Path Configuration (`/etc/nuxel/paths.conf`)

This directory ships the single source of truth for every canonical Nuxel path
(briq-20). All services, the first-boot wizard, the sandbox tooling, and the
bootstrap scripts read/parse `paths.conf` instead of hardcoding directory
literals, so a path can be changed in one place.

## Constants

| Variable                   | Default                       | Purpose                          |
|----------------------------|-------------------------------|----------------------------------|
| `NUXEL_CONFIG_DIR`         | `/etc/nuxel`                  | System configuration files       |
| `NUXEL_DATA_DIR`           | `/var/lib/nuxel`              | Persistent state root            |
| `NUXEL_PERMISSIONS_DIR`    | `/var/lib/nuxel/permissions`  | Per-app permission grants        |
| `NUXEL_NOTIFICATIONS_FILE` | `/var/lib/nuxel/notifications.json` | Canonical single-file notification history store (briq-07) |
| `NUXEL_NOTIFICATIONS_DIR`  | `/var/lib/nuxel/notifications`| LEGACY migration fallback only — see persistence section |
| `NUXEL_APP_DIR`            | `/var/app`                    | Installed app data root          |
| `NUXEL_SANDBOX_DIR`         | `/opt/nuxel/sandbox`             | Sandbox profiles / runtime       |
| `NUXEL_LOG_DIR`            | `/var/log/nuxel`              | Service log files                |
| `NUXEL_RUN_DIR`            | `/run/nuxel`                  | Runtime pid/socket dir           |
| `NUXEL_FIRSTBOOT_MARKER`   | `/var/lib/nuxel/.firstboot-complete` | First-boot marker (see briq-22) |

## Override mechanism

- The config file is read from `/etc/nuxel/paths.conf`.
- To use an alternate file set the **`NUXEL_PATHS_CONF`** environment variable
  to point at a different `paths.conf`.
- Any individual constant can still be overridden with its own environment
  variable, e.g. `NUXEL_DATA_DIR=/custom nuxel-bridge`. Environment variables
  always take precedence over the file.

## Consumers

- `services/nuxel-bridge/src/*.py`
- `services/nuxel-portal/src/portal.py`
- `services/nuxel-notifications/src/notifications.py`
- `shell/nuxel-phosh-agent/nuxel-phosh-agent.py`
- `shell/nuxel-shell/nuxel-firstboot/main.py`
- `shell/nuxel-shell/nuxel-sandbox/nftables.sh` and `sandbox.c`
- VM / mustang bootstrap scripts (installed into the target image)

## Notification persistence (briq-07, canonical single-file)

The notification daemon persists delivered/active notifications to a single
stable JSON file so a service restart does not lose history:

    NUXEL_NOTIFICATIONS_FILE=/var/lib/nuxel/notifications.json

This is the canonical single-file location. It is resolved in `_load_history_file()`
in order of precedence:

  1. `NUXEL_NOTIFICATIONS_FILE` env var (highest precedence)
  2. `NUXEL_NOTIFICATIONS_FILE` in `paths.conf`
  3. legacy `NUXEL_NOTIFICATIONS_HISTORY_FILE` / `NUXEL_NOTIFICATIONS_DIR`
     (migration fallback only, so previously persisted
     `{NUXEL_NOTIFICATIONS_DIR}/history.json` stays readable while re-written
     to the canonical single file)
  4. built-in default `/var/lib/nuxel/notifications.json`

- The systemd unit and the OpenRC notifications script pin
  `NUXEL_NOTIFICATIONS_FILE=/var/lib/nuxel/notifications.json`, and nuxel-home
  reads the same single source, so no duplicate storage locations exist.
- The store is capped at `NOTIFICATION_HISTORY_CAP` (default `200`) entries,
  oldest evicted first, on both persist and reload. This keeps both the
  on-disk file and the live in-memory store bounded.
- On startup `notifications.py:_load_history()` restores the persisted file so
  a restart survives; new notification IDs are bumped past any restored ID to
  avoid collisions. See `services/nuxel-notifications/README.md`.

## First-boot marker (briq-s1)

The first-boot marker path is globally `/var/lib/nuxel/.firstboot-complete`
(`NUXEL_FIRSTBOOT_MARKER`). Its presence means first-boot setup has **not**
finished; the wizard removes it on completion. This is consistent across the
OpenRC first-boot script, `shell/nuxel-shell/nuxel-firstboot/main.py`, and this
`paths.conf`.
