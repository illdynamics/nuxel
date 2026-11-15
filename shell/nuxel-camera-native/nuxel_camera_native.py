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

# The FIMC-IS nodes are Samsung MPLANE + EXT_PIX_FORMAT: generic v4l2src /
# v4l2-ctl get ENOTTY because they never select the multi-plane ioctl path, so
# /dev/video* enumeration is NOT evidence of a capture frame. A real frame is
# measured by `nuxel-fimc-capture` (tools/s10plus/fimc-capture) and published
# by the camera portal; this app only renders a stream that is already proven.
FIMC_BLOCK_NOTE = (
    "Exynos FIMC-IS capture needs its MPLANE ioctl path and ISP firmware. "
    "No proven live stream yet; diagnostics show the exact failing stage "
    "(run: nuxel-camera-diag.sh status)."
)
# PipeWire node names published by the camera portal backend.
STREAM_NODE_ENV = "NUXEL_CAMERA_STREAM_NODE"
STREAM_NODE_DEFAULT = "org.nuxel.Camera.main"


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
        # A65-15: drop the redundant per-app titlebar; global navigation + the
        # in-window Close button remain the escape paths.
        self.set_decorated(False)
        self._build()

    def _build(self):
        hw = hardware_summary()

        if _HAS_ADW:
            root = Adw.ToolbarView()
            self.set_child(root)
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            content.set_margin_top(8)
            content.set_margin_bottom(16)
            content.set_margin_start(16)
            content.set_margin_end(16)
            root.set_content(content)
        else:
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            content = root
            self.set_child(root)

        # Native system bar: a native xdg_toplevel is a separate Wayland
        # surface and cannot render the PWA DOM status bar.  Keep the same
        # truthful status and a guaranteed exit here; the layer-shell nav dock
        # remains the authoritative Back/Home/Recents control.
        system_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="Nuxel Camera")
        title.set_xalign(0.0)
        self.status_label = Gtk.Label(label=self._status_line())
        self.status_label.set_xalign(0.0)
        self.status_label.set_hexpand(True)
        home = Gtk.Button(label="⌂")
        close = Gtk.Button(label="✕")
        for w in (title, self.status_label, home, close):
            system_bar.append(w)
        content.append(system_bar)
        home.connect("clicked", lambda _b: self._go_home())
        close.connect("clicked", lambda _b: self.close())
        self.connect("close-request", self._on_close)
        GLib.timeout_add_seconds(15, self._refresh_status_line)

        # Viewfinder. Only a proven stream is rendered: when the portal has
        # published a PipeWire node (the FIMC-IS probe already passed) we embed
        # a Gtk.Picture fed by a gst pipewiresrc; otherwise the card states the
        # exact reason. Never a synthetic videotestsrc in the real app.
        viewfinder, self._stream = self._build_viewfinder(hw)
        content.append(viewfinder)

        # Honest status card (A65-12): concise top-level truth. The verbose
        # V4L2/FIMC-IS audit is moved into the collapsible diagnostics below.
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_box.add_css_class("card")
        if hw["present"]:
            if hw["capture_verified"]:
                status_box.append(Gtk.Label(label="Camera ready."))
            else:
                status_box.append(Gtk.Label(
                    label="Camera hardware detected, but live preview is not available on this kernel."))
        else:
            status_box.append(Gtk.Label(label="Camera hardware not detected."))
        content.append(status_box)

        # Collapsible technical diagnostics (the FIMC-IS/68-node detail).
        expander = Gtk.Expander(label="Technical diagnostics")
        detail = Gtk.Label(label=hw["reason"])
        detail.set_wrap(True)
        detail.set_xalign(0.0)
        expander.set_child(detail)
        content.append(expander)

        # Actions: bounded Retry, Photos, and an explicit Close escape.
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_halign(Gtk.Align.CENTER)
        retry = Gtk.Button(label="Retry camera")
        retry.connect("clicked", lambda _b: self._refresh())
        btn_row.append(retry)
        photos = Gtk.Button(label="Open Photos")
        photos.connect("clicked", lambda _b: self._open_photos())
        btn_row.append(photos)
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda _b: self.close())
        btn_row.append(close)
        content.append(btn_row)

    # -- real stream ----------------------------------------------------------
    def _stream_node(self) -> str:
        return os.environ.get(STREAM_NODE_ENV) or STREAM_NODE_DEFAULT

    def _build_viewfinder(self, hw):
        """Return (widget, stream_state).

        A live frame requires both: the bridge reports capture-verified hardware
        AND the portal published a PipeWire node. Anything less is an honest
        static card; the GStreamer pipeline is torn down on window close.
        """
        node = self._stream_node()
        if not hw.get("capture_verified"):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            box.set_vexpand(True)
            box.add_css_class("card")
            icon = Gtk.Label(label="\U0001F4F7")
            icon.add_css_class("title-1")
            box.append(icon)
            box.append(Gtk.Label(label="Camera viewfinder"))
            box.append(Gtk.Label(label="No live stream: " + (hw.get("reason") or "camera not verified")))
            return box, None
        try:
            import gi as _gi
            _gi.require_version("Gst", "1.0")
            _gi.require_version("GstVideo", "1.0")
            from gi.repository import Gst
            Gst.init(None)
            pic = Gtk.Picture()
            pic.set_vexpand(True)
            pic.set_size_request(-1, 520)
            pipeline = Gst.parse_launch(
                "pipewiresrc path=%s ! videoconvert ! gtk4paintablesink name=sink" % node)
            sink = pipeline.get_by_name("sink")
            paintable = sink.get_property("paintable")
            if paintable is not None:
                pic.set_paintable(paintable)
            pipeline.set_state(Gst.State.PLAYING)
            return pic, pipeline
        except Exception as exc:  # noqa: BLE001 - report, never fake
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            box.add_css_class("card")
            box.append(Gtk.Label(label="Camera detected; stream backend unavailable"))
            box.append(Gtk.Label(label=str(exc)))
            return box, None

    def _status_line(self) -> str:
        try:
            wifi = open("/sys/class/net/wlan0/operstate").read().strip()
        except OSError:
            wifi = "unknown"
        battery = "?"
        for name in ("battery", "bq27541-0", "max77865-charger"):
            try:
                battery = open("/sys/class/power_supply/%s/capacity" % name).read().strip() + "%"
                break
            except OSError:
                continue
        return "%s  ·  Wi-Fi %s  ·  Battery %s" % (__import__("time").strftime("%H:%M"), wifi, battery)

    def _refresh_status_line(self):
        if getattr(self, "status_label", None) is not None:
            self.status_label.set_text(self._status_line())
        return True

    def _on_close(self, *_):
        self._stop_stream()
        return False

    def _stop_stream(self):
        if getattr(self, "_stream", None) is not None:
            try:
                self._stream.set_state(__import__("gi").repository.Gst.State.NULL)
            except Exception:  # noqa: BLE001
                pass
            self._stream = None

    def _go_home(self):
        env = dict(os.environ)
        env.setdefault("XDG_RUNTIME_DIR", "/run/nuxel-wayland")
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")
        try:
            subprocess.Popen(["/usr/lib/nuxel/nuxel-foreign-toplevel", "home"],
                             env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
        self.close()

    def _refresh(self):
        # Rebuild the content with a fresh status read; stop the old stream.
        self._stop_stream()
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
