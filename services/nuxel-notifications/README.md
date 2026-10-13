# Nuxel Notifications daemon

System D-Bus notification service (`org.nuxel.Notifications`) on the **system
bus**. Provides a simple JSON-based API consumed by the Phosh agent and the
HTTP bridge. No FDO spec methods, no PWA relay code, no threading.

## Interfaces

| Method          | Signature | Purpose                                             |
|-----------------|-----------|-----------------------------------------------------|
| `Notify`        | `sss`     | Send a notification (`app_id`, `summary`, `body`)   |
| `GetNotifications` | ``     | Return the live in-memory notification store (JSON) |
| `CloseNotification` | `u`   | Close a single notification                         |
| `CloseAllNotifications` | ``  | Clear the live store                                |
| `NotifyHistory` | ``       | Return the persisted on-disk history (JSON array)   |
| Signal `NotificationAdded`   | `s`   | New notification (JSON payload)                |
| Signal `NotificationClosed`  | `uu`  | Closed notification (`id`, `reason`)           |

## On-disk persistence (canonical single-file location)

Delivered and active notifications are persisted to a single stable JSON file
so a restart does not lose history:

    /var/lib/nuxel/notifications.json

This is the **canonical location** declared in `configs/nuxel/` (single source,
briq-07). It is resolved by `_load_history_file()` in order of precedence:

  1. `NUXEL_NOTIFICATIONS_FILE` env var (highest precedence)
  2. `NUXEL_NOTIFICATIONS_FILE` in `paths.conf`
  3. legacy `NUXEL_NOTIFICATIONS_HISTORY_FILE` / `NUXEL_NOTIFICATIONS_DIR`
     (migration fallback so previously persisted
     `{NUXEL_NOTIFICATIONS_DIR}/history.json` stays readable while re-written
     to the canonical single file)
  4. built-in default `/var/lib/nuxel/notifications.json`

The packaged systemd unit and the OpenRC notifications script pin
`NUXEL_NOTIFICATIONS_FILE=/var/lib/nuxel/notifications.json`; nuxel-home reads
the same single source, so no duplicate storage locations exist.

### Cap & restart guarantees (briq-s2)

- **Cap eviction**: the store is capped at `NOTIFICATION_HISTORY_CAP`
  (default 200) entries, oldest (lowest id) evicted first. Eviction is applied
  both when persisting and when reloading, so the on-disk file and the live
  in-memory store stay bounded together.
- **Restart survival**: `_load_history()` runs at service start and restores the
  persisted file. The module ID counter is bumped (`_bump_id_counter`) past the
  largest restored ID so new notifications never collide with history.
- The canonical single-file `/var/lib/nuxel/notifications.json` is authoritative.
  The legacy `{NUXEL_NOTIFICATIONS_DIR}/history.json` is retained ONLY as a
  migration read path; new writes always go to the canonical single file. The
  bridge/PWAs consume notifications via D-Bus (NotifyHistory / GetNotifications),
  not by reading the file directly.

## Smoke test

Run the persistence-after-reload smoke test:

    python3 test-notifications-persistence.py

It writes a temporary history file, simulates service "restart" by
re-initialising the store from disk, and asserts that delivered notifications
survive reload while cap eviction removes the oldest entries.
