# Nuxel notification policy

- `/etc/nuxel/notifications/dnd.json` — default DND policy (this file).
- `/var/lib/nuxel/notifications/dnd.json` — current manual state, written by
  `services/nuxel-bridge/src/dnd_provider.py` through the authenticated bridge.
- `/var/lib/nuxel/notifications.json` — notification history (never deleted by DND).

DND suppresses popup/sound/haptic/LED effects. Critical/alarm exceptions are
configurable; ordinary notifications remain in history with `suppressed=true`.
