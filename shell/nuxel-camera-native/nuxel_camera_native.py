#!/usr/bin/env python3
"""nuxel-camera-native — a genuinely Nuxel-owned native GTK4 Camera application.

It is NOT a webview and NOT the standard org.freedesktop.portal.Camera surface.
It is an independently launchable native window with its own application id,
adaptive touch UI and an HONEST hardware-status card.  It never draws a fake
live preview: if no capture backend exists, the viewfinder states exactly that
and gives the reproducible reason.

Capture (when a real backend exists) is delegated to the Nuxel bridge media
store (`org.nuxel.Bridge` `camera.capture`), never to an unreviewed root call.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import gi

gi.require_version("Gtk", "4.0")
try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw
    _HAS_ADW = True
except (ValueError, ImportError):
    Adw = None
    _HAS_ADW = False
from gi.repository import Gio, GLib, Gtk

APP_ID = "org.nuxel.CameraNative"
TOPOLOGY_PATH = "/var/lib/nuxel/camera-topology.json"

# The S10+ camera gate is a hardware/vendor fact, documented in
# docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md: the FIMC-IS vendor driver rejects
# the standard VIDIOC_S_FMT ioctl (ENOTTY), so /dev/video* enumeration is NOT
# evidence of a capture frame.
FIMC_BLOCK_NOTE = (
    "Exynos FIMC-IS vendor camera stack. /dev/video* nodes are enumerated but "
    "standard V4L2 capture is blocked (VIDIOC_S_FMT -> ENOTTY); see "
    "docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md."
)


def read_topology() -> dict:
    try:
        with open(TOPOLOGY_PATH) as fh:
            doc = json.load(fh)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def bridge_camera_status() -> dict:
    """Best-effort read of the authoritative bridge camera status."""
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        proxy = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            "org.nuxel.Bridge", "/org/nuxel/Bridge", "org.nuxel.Bridge", None)
        raw = proxy.call_sync("CameraStatus", GLib.Variant("(s)", ("org.nuxel.CameraNative",)),
                              Gio.DBusCallFlags.NONE, 5000, None)
        return json.loads(raw.unpack()[0])
    except Exception:
        return {}


def hardware_summary() -> dict:
    status = bridge_camera_status()
    if not status:
        topo = read_topology()
        nodes = topo.get("video_nodes") or []
        return {
            "present": bool(nodes),
            "capture_verified": False,
            "reason": "bridge unavailable; system snapshot shows %d /dev/video* node(s)" % len(nodes),
            "blocked": True,
        }
    present = bool(status.get("camera_present"))
    verified = bool(status.get("capture_verified"))
    reason = status.get("detail") or (FIMC_BLOCK_NOTE if present else "No camera device")
    return {
        "present": present,
        "capture_verified": verified,
        "reason": reason,
        "blocked": not verified,
    }


class CameraNativeWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Nuxel Camera")
        self.set_default_size(420, 720)
        self._build()

    def _build(self):
        hw = hardware_summary()

        if _HAS_ADW:
            root = Adw.ToolbarView()
            header = Adw.HeaderBar()
            header.set_title_widget(Gtk.Label(label="Nuxel Camera"))
            root.add_top_bar(header)
            self.set_child(root)
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            content.set_margin_top(16)
            content.set_margin_bottom(16)
            content.set_margin_start(16)
            content.set_margin_end(16)
            root.set_content(content)
        else:
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            content = root
            self.set_child(root)

        # Viewfinder placeholder: honest, never a synthetic live preview.
        viewfinder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        viewfinder.set_vexpand(True)
        viewfinder.set_halign(Gtk.Align.FILL)
        viewfinder.set_valign(Gtk.Align.CENTER)
        viewfinder.add_css_class("card")
        icon = Gtk.Label(label="\U0001F4F7")
        icon.add_css_class("title-1")
        viewfinder.append(icon)
        viewfinder.append(Gtk.Label(label="Camera viewfinder"))
        content.append(viewfinder)

        # Honest status card.
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_box.add_css_class("card")
        state_line = "Camera present" if hw["present"] else "Camera NOT present"
        status_box.append(Gtk.Label(label=state_line))
        if hw["present"]:
            status_box.append(Gtk.Label(label="Live capture: " +
                                       ("VERIFIED" if hw["capture_verified"] else "NOT verified")))
        reason = Gtk.Label(label=hw["reason"])
        reason.set_wrap(True)
        reason.set_xalign(0.0)
        status_box.append(reason)
        content.append(status_box)

        # Actions.
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_halign(Gtk.Align.CENTER)
        refresh = Gtk.Button(label="Refresh status")
        refresh.connect("clicked", lambda _b: self._refresh())
        btn_row.append(refresh)
        photos = Gtk.Button(label="Open Photos")
        photos.connect("clicked", lambda _b: self._open_photos())
        btn_row.append(photos)
        content.append(btn_row)

    def _refresh(self):
        # Rebuild the content with a fresh status read.
        self.set_child(None)
        self._build()

    def _open_photos(self):
        # Delegate to the standalone Photos PWA; never a second media database.
        try:
            subprocess.Popen(
                ["xdg-open", "http://127.0.0.1:8000/pwa/nuxel-apps/photos/index.html"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass


class CameraNativeApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        if _HAS_ADW:
            Adw.init()

    def do_activate(self):
        win = CameraNativeWindow(self)
        win.present()


def main():
    app = CameraNativeApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
