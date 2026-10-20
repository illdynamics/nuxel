#!/usr/bin/env python3
"""Nuxel Camera Portal backend.

Implements a minimal xdg-desktop-portal-style camera backend that exposes the
``org.freedesktop.portal.Camera`` interface (ScreenCast-style RunCamera) over
D-Bus and hands the requesting PWA a PipeWire node id / file descriptor for the
camera stream.

Two backends:

* **VM / synthetic** — when no real camera is present (e.g. the ARM64 UTM/Fedora
  VM), a GStreamer ``videotestsrc`` color-bar node is published on the session
  PipeWire socket so the Chain
  ``PWA -> HTTP API -> nuxel-bridge -> xdg-desktop-portal -> Camera backend``
  still works end to end.
* **hardware** — on mustang (Phase 2) the backend publishes the real
  ``v4l2src`` node for the Samsung ISOCELL main camera and the front camera.

Requirements: ``python3-gi``, ``python3-gst`` and the ``GstPipeWire`` plugin.
The systemd unit ships as ``shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service``.

Design notes live in ``docs/camera-geolocation-design.md``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("nuxel-camera-portal")

# ---------------------------------------------------------------------------
# D-Bus object model
#
# The org.freedesktop.portal.Camera interface is declared from a D-Bus
# introspection XML string (see _CAMERA_INTROSPECTION_XML below) that is parsed
# into a Gio.DBusNodeInfo. The object is then exported with
# Gio.DBusConnection.register_object(DBUS_PATH, node_info,
# _method_call_closure) — the second positional argument is the node info and
# the third is a PyGObject method-call closure, NOT a bare Python object.
#
# Camera: org.freedesktop.portal.Camera
#        + RunCamera(a{sv} options) -> o handle        (single out value)
#        + Release(o handle) -> ()
#        + AvailableCameras(a{sv} options) -> a{sv}    (state/cameras)
#        + Subscribe(on_changed, o handle) -> ()
#        + Unsubscribe(o handle) -> ()
# ---------------------------------------------------------------------------

DBUS_NAME = "org.freedesktop.portal.Camera"
DBUS_PATH = "/org/freedesktop/portal/camera"

# Global backend handles the PipeWire node management.
_BACKEND = None


class CameraBackend:
    """Owns a GStreamer pipeline that publishes a PipeWire camera node."""

    def __init__(self, synthetic: bool = True, video_source: str | None = None):
        self.synthetic = synthetic
        self.node_id = 0
        self.session_label = None
        self._pipeline = None
        self._bus_watch_id = 0
        self._source = "synthetic-colorbar" if synthetic else (video_source or "/dev/video0")
        self._gst_error = None
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
            Gst.init(None)
            self.Gst = Gst
            self._has_gst = True
        except Exception as exc:  # pragma: no cover - environment dependent
            log.error("GStreamer bindings unavailable: %s", exc)
            self._has_gst = False
            self._gst_error = str(exc)
            return

        if synthetic:
            # GStreamer videotestsrc -> PipeWire sink (color bars for the VM)
            pipestr = (
                "videotestsrc ! video/x-raw,format=NV12,width=1920,height=1080,"
                "framerate=30/1 ! videoconvert ! queue ! "
                "pipewiresink name=pwsink node.name=org.nuxel.Camera.synthetic"
            )
            self._source = "synthetic-colorbar"
        else:
            # Real camera pipeline (mustang). Use v4l2src pointing at the usual
            # SoC camera device; override with --video-source from CLI.
            device = video_source or "/dev/video0"
            pipestr = (
                f"v4l2src device={device} ! video/x-raw,format=NV12,"
                "width=1440,height=3120,"
                "framerate=30/1 ! videoconvert ! queue ! "
                "pipewiresink name=pwsink node.name=org.nuxel.Camera.main"
            )
            self._source = device

        try:
            self._pipeline = self.Gst.parse_launch(pipestr)
            self._bus = self._pipeline.get_bus()
            self._bus.add_signal_watch()
        except Exception as exc:  # pragma: no cover
            log.error("Failed to build camera pipeline: %s", exc)
            self._pipeline = None

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> bool:
        if self._pipeline is None:
            return False
        if self._bus_watch_id:
            self._bus_watch_id += 1  # keep watch alive
        ret = self._pipeline.set_state(self.Gst.State.PLAYING)
        return ret != self.Gst.StateChangeReturn.FAILURE

    def stop(self) -> None:
        if self._pipeline is None:
            return
        self._pipeline.set_state(self.Gst.State.NULL)
        if self._bus_watch_id:
            self._bus_watch_id = 0

    def get_node_id(self) -> int:
        """Return the PipeWire node id of the camera sink, if discoverable.

        Once the pipeline is PLAYING the ``pipewiresink`` element has registered
        the node with the session PipeWire daemon and exposes the resulting node
        id via its ``node.id`` GObject property. Read that value (rather than a
        hardcoded constant) and cache it on ``self.node_id``.
        """
        if self._pipeline is None:
            return 0
        sink = self._pipeline.get_by_name("pwsink")
        if sink is None:
            return self.node_id
        try:
            node_id = sink.get_property("node.id")
            if node_id:
                self.node_id = int(node_id)
            else:
                log.debug("pipewiresink node.id not populated yet")
        except Exception as exc:  # pragma: no cover - binder/plugin dependent
            log.debug("PipeWire node.id discovery failed: %s", exc)
        return self.node_id

    def available_state(self) -> dict:
        return {
            "cameras": [
                {
                    "id": "synthetic" if self.synthetic else "main",
                    "source": self._source,
                    "synthetic": self.synthetic,
                    "capabilities": ["camera:capture", "camera:preview"],
                }
            ],
            "active": self.node_id != 0 or self._has_gst,
            "gst_ok": bool(getattr(self, "_has_gst", False)),
            "gst_error": getattr(self, "_gst_error", None),
        }


def build_synthetic_pipeline():  # convenience alias for docs / tests
    return CameraBackend(synthetic=True)


# ---------------------------------------------------------------------------
# GLib D-Bus service
# ---------------------------------------------------------------------------


def _run_dbus_service(backend: CameraBackend, system_bus: bool = False):
    import gi  # noqa: F401 - imported lazily so --help works on bare hosts

    gi.require_version("Gio", "2.0")
    gi.require_version("GLib", "2.0")
    from gi.repository import Gio, GLib

    bus_type = Gio.BusType.SYSTEM if system_bus else Gio.BusType.SESSION
    bus = Gio.bus_get_sync(bus_type, None)
    # Allow replacing any previous instance.
    request_name_flags = (
        Gio.BusNameOwnerFlags.ALLOW_REPLACEMENT
        | Gio.BusNameOwnerFlags.REPLACE
    )
    owner_id = bus.own_name_on_connection(
        DBUS_NAME,
        0,
        request_name_flags,
        None,
        None,
    )
    # Expose the backend to the method-call closure (the closure is stateless
    # and looks up the current backend each call).
    global _BACKEND
    _BACKEND = backend
    # Parse the introspection XML into a Gio.DBusNodeInfo describing the
    # org.freedesktop.portal.Camera interface, then export the object with a
    # PyGObject method-call closure. DoRunCamera returns exactly one out value
    # (an object path), matching the declared `o` out signature.
    node_info = Gio.DBusNodeInfo.new_for_xml(_CAMERA_INTROSPECTION_XML)
    bus.register_object(
        DBUS_PATH,
        node_info,
        _method_call_closure,
    )
    log.info("Camera portal '%s' on %s bus registered", DBUS_NAME, bus_type)

    def _on_bus_message(bus_instance, message):
        # minimal signal pump; leave to main loop
        pass

    loop = GLib.MainLoop()

    def _quit(*_):
        loop.quit()

    import signal as _signal

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 2, _quit)  # SIGINT
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 15, _quit)  # SIGTERM

    # Start the camera pipeline when the service comes up (VM default).
    if backend.synthetic:
        ok = backend.start()
        log.info("Camera pipeline (synthetic) started: %s", ok)
        # Discover the real PipeWire node id from the started pipewiresink
        # instead of a hardcoded constant, so the VM smoke test can validate a
        # live node id is returned.
        backend.node_id = backend.get_node_id()
        log.info("Camera PipeWire node id discovered: %d", backend.node_id)

    loop.run()


# D-Bus introspection XML describing org.freedesktop.portal.Camera.
_CAMERA_INTROSPECTION_XML = """<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
"http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node name="/org/freedesktop/portal/camera">
  <interface name="org.freedesktop.portal.Camera">
    <method name="AvailableCameras">
      <arg type="a{sv}" name="options" direction="in"/>
      <arg type="a{sv}" name="cameras" direction="out"/>
    </method>
    <method name="RunCamera">
      <arg type="a{sv}" name="options" direction="in"/>
      <arg type="o" name="handle" direction="out"/>
    </method>
    <method name="Release">
      <arg type="o" name="handle" direction="in"/>
    </method>
    <method name="Subscribe">
      <arg type="s" name="on_changed" direction="in"/>
      <arg type="o" name="handle" direction="in"/>
    </method>
    <method name="Unsubscribe">
      <arg type="o" name="handle" direction="in"/>
    </method>
  </interface>
</node>"""


class CameraPortalNode:
    """D-Bus object implementing org.freedesktop.portal.Camera.

    Rather than being passed as the raw object, this class is driven by the
    module-level :func:`_method_call_closure` which is registered via
    Gio.DBusConnection.register_object(DBUS_PATH, node_info, closure). Each
    method handler returns exactly the values the declared D-Bus out
    signature expects (a single value for RunCamera, not a 2-tuple).
    """

    def __init__(self, backend: CameraBackend):
        self._backend = backend
        self._handle = None

    def run_camera(self) -> str:
        global _BACKEND
        _BACKEND = self._backend
        # Start the stream, then discover and return the real PipeWire node id
        # so the camera PWA can attach to it (docs/camera-geolocation-design.md
        # documents that the RunCamera response carries the node_id). The handle
        # is encoded as a D-Bus object path carrying that node id, which both
        # satisfies the declared `o` out signature and exposes the node id.
        self._backend.start()
        node_id = self._backend.get_node_id()
        self._handle = f"/org/nuxel/camera/{node_id}"
        return self._handle

    def release(self) -> None:
        # Stop publishing the node; real devices stop the stream.
        self._backend.stop()

    def available_cameras(self) -> dict:
        return self._backend.available_state()

    def subscribe(self, on_changed: str = "") -> None:
        # Real backends subscribe to CameraFlagsChanged; minimal backend is a
        # no-op but must exist to answer the D-Bus call.
        return

    def unsubscribe(self) -> None:
        return


def _method_call_closure(
    connection,
    sender_name,
    object_path,
    interface_name,
    method_name,
    parameters,
    invocation,
):
    """PyGObject method-call callback for Gio.DBusConnection.register_object.

    Signature is fixed by PyGObject: (connection, sender, object_path,
    interface_name, method_name, parameters, invocation). Dispatch to the
    matching handler and reply with a GLib.Variant built from the declared
    out signature (RunCamera returns exactly one `o` value).
    """
    global _BACKEND
    try:
        gi = __import__("gi")
        gi.require_version("GLib", "2.0")
        from gi.repository import GLib

        backend = _BACKEND
        node = CameraPortalNode(backend if backend is not None else CameraBackend())

        if interface_name != "org.freedesktop.portal.Camera":
            invocation.return_error(
                GLib.Error(
                    "org.freedesktop.DBus.Error.UnknownMethod",
                    "Unknown method %s on %s" % (method_name, interface_name),
                )
            )
            return

        if method_name == "RunCamera":
            handle = node.run_camera()
            # Declared out signature: `o` (a single D-Bus object path).
            invocation.return_value(GLib.Variant("o", handle))
        elif method_name == "Release":
            node.release()
            invocation.return_value(None)
        elif method_name == "AvailableCameras":
            state = node.available_cameras()
            # Declared out signature: a{sv}.
            variant_dict = {}
            for key, value in state.items():
                if isinstance(value, bool):
                    variant_dict[key] = GLib.Variant("b", value)
                elif isinstance(value, int):
                    variant_dict[key] = GLib.Variant("i", value)
                elif isinstance(value, list):
                    variant_dict[key] = GLib.Variant("as", [str(v) for v in value])
                else:
                    variant_dict[key] = GLib.Variant("s", str(value))
            invocation.return_value(GLib.Variant("a{sv}", variant_dict))
        elif method_name == "Subscribe":
            on_changed = ""
            if parameters is not None and parameters.n_children() > 0:
                on_changed = parameters.get_child_value(0).get_string()
            node.subscribe(on_changed)
            invocation.return_value(None)
        elif method_name == "Unsubscribe":
            node.unsubscribe()
            invocation.return_value(None)
        else:
            invocation.return_error(
                GLib.Error(
                    "org.freedesktop.DBus.Error.UnknownMethod",
                    "Unknown method %s" % method_name,
                )
            )
    except Exception as exc:  # pragma: no cover - defensive error reply
        log.error("Method-call dispatch failed for %s: %s", method_name, exc)
        try:
            invocation.return_error(
                GLib.Error("org.freedesktop.portal.Camera.Error.Failed", str(exc))
            )
        except Exception:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="nuxel-camera-portal",
        description="Nuxel minimal xdg-desktop-portal camera backend",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Publish a synthetic color-bar camera node (VM default).",
    )
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Publish the real camera node (mustang Phase 2).",
    )
    parser.add_argument(
        "--video-source",
        default=None,
        help="v4l2 device for hardware mode (default /dev/video0).",
    )
    parser.add_argument(
        "--system-bus",
        action="store_true",
        help="Register on the system bus (requires root); default session bus.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Print a JSON status record (for smoke tests) and exit.",
    )
    args = parser.parse_args(argv)

    if args.once:
        backend = CameraBackend(synthetic=not args.hardware, video_source=args.video_source)
        print(json.dumps({"status": "ok", **backend.available_state()}))
        return 0

    synthetic = not args.hardware  # default to synthetic unless --hardware
    backend = CameraBackend(synthetic=synthetic, video_source=args.video_source)
    _run_dbus_service(backend, system_bus=args.system_bus)
    return 0


if __name__ == "__main__":
    sys.exit(main())
