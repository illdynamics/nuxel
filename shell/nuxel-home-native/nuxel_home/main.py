"""Nuxel Home — Native GTK4 Home Screen

Adw.Application with:
  - Fullscreen window, no desktop chrome
  - Top status bar: time, network, battery, notification count
  - App grid with drag-reorder, tap-to-launch
  - PWA launch via chromium --app=URL
  - Native-placeholder shows toast
  - Exit with Ctrl+Q or Escape twice
  - Periodic status polling (GLib.timeout_add_seconds)
  - D-Bus notification polling (NotificationPoller)

CLI flags:
  --debug          Enable DEBUG-level logging
  --reset-layout   Reset app grid order to factory defaults
  --safe-mode      Start without launching any apps
"""

import argparse
import logging
import os
import signal
import sys
from typing import Optional
import time as time_module

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from .app_launcher import launch_pwa
from .app_model import AppRegistry, AppDef
from .dbus_client import NuxelDBusClient
from .launcher_grid import LauncherGrid
from .notifications import NotificationPoller
from .system_status import (
    get_battery_status,
    get_current_time,
    get_full_status,
    get_network_status,
)

logger = logging.getLogger(__name__)

# Interval for status bar updates (seconds)
STATUS_POLL_INTERVAL = 5

# Exit key handling
ESCAPE_EXIT_DELAY_MS = 500  # window to press Escape twice


def setup_logging(debug: bool = False):
    """Configure logging to both stderr and ~/.local/state/nuxel/home.log.

    Args:
        debug: If True, set logging level to DEBUG instead of INFO.
    """
    log_dir = os.path.expanduser("~/.local/state/nuxel")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "home.log")

    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # File handler — always DEBUG detail to file
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    # Stderr handler — respect the --debug flag level
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(level)
    sh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # root catches everything; handlers filter
    root.addHandler(fh)
    root.addHandler(sh)


class NuxelHomeApp(Adw.Application):
    """Main Nuxel Home application.

    Manages the fullscreen window, status bar, app grid, D-Bus client,
    and notification polling.
    """

    def __init__(self, reset_layout: bool = False, safe_mode: bool = False, **kwargs):
        super().__init__(
            application_id="org.nuxel.Home",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
            **kwargs
        )
        self._reset_layout = reset_layout
        self._safe_mode = safe_mode
        self._window: Optional[Adw.ApplicationWindow] = None
        self._status_bar: Optional[Gtk.Box] = None
        self._status_time: Optional[Gtk.Label] = None
        self._status_network: Optional[Gtk.Label] = None
        self._status_battery_icon: Optional[Gtk.Label] = None
        self._status_battery_pct: Optional[Gtk.Label] = None
        self._status_notif_count: Optional[Gtk.Label] = None
        self._launcher_grid: Optional[LauncherGrid] = None
        self._registry = AppRegistry()
        self._dbus = NuxelDBusClient()
        self._notif_poller = NotificationPoller(self._dbus)
        self._poll_timer_id: Optional[int] = None
        self._escape_press_count = 0
        self._escape_reset_id: Optional[int] = None

        # Register signals
        self.connect("activate", self._on_activate)

    # ── Application lifecycle ────────────────────────────────────

    def _on_activate(self, app):
        """Build and show the main window."""
        if self._window is not None:
            self._window.present()
            return

        if self._safe_mode:
            logger.info("--safe-mode: starting without app launching")

        # Handle --reset-layout before building UI
        if self._reset_layout:
            logger.info("--reset-layout: resetting app grid order to factory defaults")
            self._registry.reset_order()

        # Create the Adw application window
        self._window = Adw.ApplicationWindow(application=app)
        self._window.set_title("Nuxel")
        self._window.get_style_context().add_class("nuxel-home-window")
        self._window.set_default_size(420, 820)

        # Make fullscreen
        self._window.fullscreen()

        # Build UI
        self._build_ui()

        # Set up keyboard shortcuts
        self._setup_keyboard()

        # Start status polling (GLib.timeout_add_seconds)
        self._start_status_polling()

        # Start D-Bus notification polling
        self._notif_poller.start()

        self._window.connect("destroy", self._on_destroy)
        # GTK4: widgets are visible by default

    def _on_destroy(self, window):
        """Clean up on window close."""
        self._stop_status_polling()
        self._notif_poller.stop()
        self._window = None

    # ── UI construction ──────────────────────────────────────────

    def _build_ui(self):
        """Assemble the vertical layout: status bar + launcher grid."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # ── Status bar ───────────────────────────────────────────
        self._status_bar = self._build_status_bar()
        main_box.append(self._status_bar)

        # ── Launcher grid ────────────────────────────────────────
        self._launcher_grid = LauncherGrid(self._registry)
        self._launcher_grid.connect("app-launch", self._on_app_launch)
        main_box.append(self._launcher_grid)

        self._window.set_child(main_box)

    def _build_status_bar(self) -> Gtk.Box:
        """Build the top status bar with time, network, battery, notifications."""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.get_style_context().add_class("status-bar")
        bar.set_hexpand(True)

        # Time (left)
        self._status_time = Gtk.Label(label=get_current_time())
        self._status_time.get_style_context().add_class("status-time")
        self._status_time.set_halign(Gtk.Align.START)
        bar.prepend(self._status_time)

        # Spacer
        center_box = Gtk.Box()
        center_box.set_hexpand(True)
        bar.append(center_box)

        # Network icon (right side cluster)
        self._status_network = Gtk.Label(label="🛜")
        self._status_network.get_style_context().add_class("status-network-icon")
        bar.append(self._status_network)

        # Battery percentage
        self._status_battery_pct = Gtk.Label(label="100%")
        self._status_battery_pct.get_style_context().add_class("status-battery-level")
        bar.append(self._status_battery_pct)

        # Battery icon
        self._status_battery_icon = Gtk.Label(label="🔋")
        self._status_battery_icon.get_style_context().add_class("status-battery-icon")
        bar.append(self._status_battery_icon)

        # Notification count badge
        self._status_notif_count = Gtk.Label(label="")
        self._status_notif_count.get_style_context().add_class("status-notification-count")
        self._status_notif_count.set_visible(False)
        bar.append(self._status_notif_count)

        return bar

    # ── Keyboard shortcuts ───────────────────────────────────────

    def _setup_keyboard(self):
        """Bind Ctrl+Q and Escape double-press for exit via key controller."""
        # Single GTK4 key controller for all shortcuts
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self._window.add_controller(key_controller)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle key events — Ctrl+Q quit, Escape double-press for exit."""
        # Ctrl+Q → quit
        if (state & Gdk.ModifierType.CONTROL_MASK) and keyval == Gdk.KEY_q:
            logger.info("Ctrl+Q — quitting")
            self.quit()
            return True

        # Escape → track double-press for exit
        if keyval == Gdk.KEY_Escape:
            self._escape_press_count += 1

            if self._escape_press_count >= 2:
                logger.info("Double Escape — quitting")
                self.quit()
                return True

            # Reset counter after delay
            if self._escape_reset_id is not None:
                GLib.source_remove(self._escape_reset_id)
            self._escape_reset_id = GLib.timeout_add(
                ESCAPE_EXIT_DELAY_MS,
                self._reset_escape,
            )
            return True

        return False

    def _reset_escape(self) -> bool:
        self._escape_press_count = 0
        self._escape_reset_id = None
        return False

    # ── App launch handling ──────────────────────────────────────

    def _on_app_launch(self, grid, app_id):
        """Handle app launch from the grid."""
        app = self._registry.get(app_id)
        if app is None:
            logger.warning("Unknown app ID: %s", app_id)
            return

        if self._safe_mode:
            logger.info("Safe mode — launch blocked for: %s", app_id)
            self._launcher_grid.show_toast("Safe mode — launch disabled")
            return

        if app.is_pwa():
            self._launch_pwa(app)
        elif app.is_native_placeholder():
            self._launch_native_app(app)
        else:
            logger.warning("Unknown app kind: %s", app.kind)

    def _launch_pwa(self, app: AppDef):
        """Launch a PWA in a dedicated Chromium window."""
        logger.info("Launching PWA: %s (%s)", app.name, app.url)
        ok = launch_pwa(app.name, app.url)
        if ok:
            self._launcher_grid.show_toast(f"Opening {app.name}…")
        else:
            self._launcher_grid.show_toast(
                f"Could not launch {app.name} — Chromium not found",
                duration_ms=4000,
            )

    def _launch_native_app(self, app: AppDef):
        """Launch a native binary if it exists, otherwise show placeholder toast."""
        logger.info("Native app tapped: %s", app.name)

        native_binary = getattr(app, 'native_binary', None)
        if native_binary:
            import subprocess
            import shutil
            if shutil.which(native_binary):
                logger.info("Launching native binary: %s", native_binary)
                try:
                    subprocess.Popen(
                        [native_binary],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self._launcher_grid.show_toast(f"Opening {app.name}…")
                    return
                except Exception as exc:
                    logger.error("Failed to launch native binary %s: %s", native_binary, exc)

        # Fallback: show placeholder toast
        logger.info("Placeholder app tapped: %s", app.name)
        self._launcher_grid.show_toast(
            f"{app.name} — app not implemented yet",
            duration_ms=3000,
        )

    # ── Status polling (GLib.timeout_add_seconds) ────────────────

    def _start_status_polling(self):
        """Start periodic status updates."""
        self._update_status()
        self._poll_timer_id = GLib.timeout_add_seconds(
            STATUS_POLL_INTERVAL,
            self._update_status,
        )

    def _stop_status_polling(self):
        """Stop status polling."""
        if self._poll_timer_id is not None:
            GLib.source_remove(self._poll_timer_id)
            self._poll_timer_id = None

    def _update_status(self) -> bool:
        """Poll system status and update UI labels.

        Returns True to keep the GLib timeout active.
        """
        try:
            # Time
            now = get_current_time()
            if self._status_time:
                self._status_time.set_label(now)

            # Network
            net = get_network_status()
            if self._status_network:
                if net.get("wifi"):
                    self._status_network.set_label("🛜")
                elif net.get("ethernet"):
                    self._status_network.set_label("🌐")
                else:
                    self._status_network.set_label("📶")

            # Battery
            bat = get_battery_status()
            level = bat.get("level", 100)
            charging = bat.get("charging", False)

            if self._status_battery_pct:
                self._status_battery_pct.set_label(f"{level}%")
                # Apply class for critical/warning levels
                ctx = self._status_battery_pct.get_style_context()
                if level <= 10:
                    ctx.add_class("status-battery-critical")
                elif level <= 20:
                    ctx.add_class("status-battery-warning")
                else:
                    ctx.remove_class("status-battery-critical")
                    ctx.remove_class("status-battery-warning")

            if self._status_battery_icon:
                if charging:
                    self._status_battery_icon.set_label("⚡")
                elif level <= 10:
                    self._status_battery_icon.set_label("🪫")
                else:
                    self._status_battery_icon.set_label("🔋")

            # Notifications — use NotificationPoller
            notif_count = self._notif_poller.get_count()

            if self._status_notif_count:
                if notif_count > 0:
                    self._status_notif_count.set_label(str(notif_count))
                    self._status_notif_count.set_visible(True)
                else:
                    self._status_notif_count.set_visible(False)

        except Exception as exc:
            logger.warning("Status update error: %s", exc)

        return True  # keep timer alive

    # ── Error handling / recovery ────────────────────────────────

    def _on_error(self, message: str):
        """Show a non-fatal error in the UI."""
        logger.error(message)
        if self._launcher_grid:
            self._launcher_grid.show_toast(f"Error: {message}", duration_ms=5000)


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Nuxel Home — Native GTK4 Home Screen",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable DEBUG-level logging output",
    )
    parser.add_argument(
        "--reset-layout",
        action="store_true",
        default=False,
        help="Reset app grid order to factory defaults",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        default=False,
        help="Start without launching any apps",
    )
    return parser.parse_args(argv)


def main():
    """Entry point for nuxel-home-native."""
    args = parse_args()
    setup_logging(debug=args.debug)

    logger.info("Starting Nuxel Home v0.6.0-beta")
    if args.debug:
        logger.info("Debug logging enabled")
    if args.reset_layout:
        logger.info("Reset layout flag set — will clear saved order on startup")
    if args.safe_mode:
        logger.info("Safe mode enabled — app launching blocked")

    # Ensure Adwaita is initialized
    Adw.init()

    app = NuxelHomeApp(reset_layout=args.reset_layout, safe_mode=args.safe_mode)

    # Handle SIGINT gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    exit_code = app.run([sys.argv[0]])
    logger.info("Nuxel Home exited (code %d)", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
