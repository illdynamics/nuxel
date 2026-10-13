"""Nuxel Home — D-Bus Notification Poller

Polls org.nuxel.Notifications.GetNotifications every 5 seconds
via GLib.timeout_add, tracks unseen count, and exposes get_count()
for the status bar.

Maintains a rolling set of seen notification IDs so only *new*
notifications increment the unseen count.
"""

import logging
from typing import List, Set

from gi.repository import GLib

from .dbus_client import NuxelDBusClient, NotificationInfo

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 5


class NotificationPoller:
    """Polls D-Bus for notifications and tracks unseen count.

    Usage:
        poller = NotificationPoller(dbus_client)
        poller.start()    # begins GLib timeout loop
        count = poller.get_count()
        poller.stop()     # removes timeout
        poller.mark_seen()  # reset unseen count to zero
    """

    def __init__(self, dbus: NuxelDBusClient):
        self._dbus = dbus
        self._unseen_count: int = 0
        self._seen_ids: Set[str] = set()
        self._poll_id: int = 0
        self._running = False

    # ── Lifecycle ────────────────────────────────────────────────

    def start(self) -> None:
        """Begin periodic polling with GLib.timeout_add."""
        if self._running:
            return
        self._running = True
        # Fire immediately, then every POLL_INTERVAL_S seconds
        self._poll()
        self._poll_id = GLib.timeout_add_seconds(POLL_INTERVAL_S, self._poll)
        logger.info("NotificationPoller started (interval=%ds)", POLL_INTERVAL_S)

    def stop(self) -> None:
        """Remove the GLib timeout source."""
        if not self._running:
            return
        self._running = False
        if self._poll_id:
            GLib.source_remove(self._poll_id)
            self._poll_id = 0
        logger.info("NotificationPoller stopped")

    # ── Public API ───────────────────────────────────────────────

    def get_count(self) -> int:
        """Return the number of unseen notifications."""
        return self._unseen_count

    def mark_seen(self) -> None:
        """Reset the unseen count to zero.

        Call after the user has seen the notification indicator
        (e.g. opening the notification panel).
        """
        self._unseen_count = 0

    # ── Internal polling ─────────────────────────────────────────

    def _poll(self) -> bool:
        """Fetch current notifications and update unseen count.

        Returns True so GLib keeps the timeout alive.
        """
        if not self._running:
            return False

        try:
            raw = self._dbus.notifications_get_all()
        except Exception as exc:
            logger.debug("Notification poll failed: %s", exc)
            return True

        current_ids = self._make_ids(raw)

        # Count notifications we haven't seen before
        new_ids = current_ids - self._seen_ids
        self._unseen_count += len(new_ids)

        # Merge into seen set
        self._seen_ids |= current_ids

        # Prune IDs that no longer exist (notification dismissed)
        self._seen_ids &= current_ids

        return True  # keep timeout alive

    @staticmethod
    def _make_ids(notifs: List[NotificationInfo]) -> Set[str]:
        """Build a set of stable-ish IDs from notification content.

        Since we don't have a real notification ID from D-Bus,
        we combine app_name + title + body into a fingerprint.
        """
        ids: Set[str] = set()
        for n in notifs:
            fp = f"{n.app_name}|{n.title}|{n.body}"
            ids.add(fp)
        return ids
