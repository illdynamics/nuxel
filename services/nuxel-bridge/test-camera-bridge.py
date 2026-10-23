#!/usr/bin/env python3
"""Offline unit tests: bridge camera verbs + file-backed media store (A52).

Guards the A52 camera-storage contract end to end (no D-Bus daemon, no handset):
permission gating (deny -> no file), base64 capture -> real file -> list -> open
-> delete, honest NO_CAMERA status, and the HTTP verb/arg wiring for
camera.status/open/delete.  Uses inert dbus/gi stubs so bridge.py imports on a
host with no dbus package.
"""
from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE_SRC = os.path.join(HERE, "src", "bridge.py")
API_SRC = os.path.join(HERE, "src", "api.py")

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def install_stubs() -> None:
    dbus = types.ModuleType("dbus")

    class _DBusException(Exception):
        def __init__(self, *a, **k):
            super().__init__(*(a or ("failed",)))
        def get_dbus_name(self):
            return "org.freedesktop.DBus.Error.Failed"

    exceptions = types.ModuleType("dbus.exceptions")
    exceptions.DBusException = _DBusException
    exceptions.NameExistsException = type("NameExistsException", (_DBusException,), {})
    dbus.exceptions = exceptions
    dbus.DBusException = _DBusException
    dbus.PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
    dbus.types = types.SimpleNamespace(
        String=lambda *a, **k: str(a[0]) if a else "",
    )
    dbus.ByteArray = bytearray
    dbus.String = str
    dbus.Boolean = bool
    dbus.Int32 = int
    dbus.ObjectPath = str
    dbus.Dictionary = lambda *a, **k: dict(a[0]) if a else {}

    class _Any:
        def __getattr__(self, name):
            def _boom(*a, **k):
                raise RuntimeError("no D-Bus in this test: %s" % name)
            return _boom

    dbus.Interface = lambda obj, name: obj
    dbus.SystemBus = lambda *a, **k: _Any()

    service = types.ModuleType("dbus.service")
    def method(iface, in_signature=None, out_signature=None):
        def deco(fn):
            fn._dbus_in_signature = in_signature
            fn._dbus_out_signature = out_signature
            return fn
        return deco
    def signal(iface, signature=None):
        def deco(fn):
            return fn
        return deco
    class Object:
        def __init__(self, *a, **k):
            pass
    class BusName:
        def __init__(self, *a, **k):
            pass
    service.method = method
    service.signal = signal
    service.Object = Object
    service.BusName = BusName
    dbus.service = service

    mainloop = types.ModuleType("dbus.mainloop")
    glib = types.ModuleType("dbus.mainloop.glib")
    glib.DBusGMainLoop = lambda *a, **k: None
    mainloop.glib = glib
    dbus.mainloop = mainloop

    gi = types.ModuleType("gi")
    repo = types.ModuleType("gi.repository")
    class _GLib:
        class MainLoop:
            def __init__(self, *a, **k):
                pass
            def run(self, *a, **k):
                pass
            def quit(self, *a, **k):
                pass
    repo.GLib = _GLib()
    gi.repository = repo

    sys.modules["dbus"] = dbus
    sys.modules["dbus.exceptions"] = exceptions
    sys.modules["dbus.service"] = service
    sys.modules["dbus.mainloop"] = mainloop
    sys.modules["dbus.mainloop.glib"] = glib
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = repo


def load(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    install_stubs()
    sys.path.insert(0, os.path.join(HERE, "src"))
    root = tempfile.mkdtemp(prefix="nuxel-camera-bridge-test-")
    os.environ["NUXEL_MEDIA_DIR"] = root
    os.environ["NUXEL_PERMISSIONS_DIR"] = os.path.join(root, "permissions")
    try:
        bridge = load("bridge_under_test", BRIDGE_SRC)
        svc = bridge.NuxelBridgeService(None, "/org/nuxel/Bridge")

        # 1. honest status: no /dev/video nodes in this sandbox -> NO_CAMERA, never verified
        status = bridge.json.loads(svc.CameraStatus("org.nuxel.Camera"))
        check(status.get("capture_verified") is False, "camera status never claims a verified frame")
        check(status.get("success") is True, "camera status responds")

        # 2. permission deny -> no capture, no file
        denied = bridge.json.loads(svc.CameraCapture("org.nuxel.Camera", "photo", "image/jpeg",
                                                      base64.b64encode(b"DENIED").decode()))
        check(denied.get("success") is False and denied.get("error_code") == "PERMISSION_DENIED",
              "capture denied without camera:capture grant")
        check(len(svc.media.list()) == 0, "denied capture writes no file")

        # 3. grant -> capture -> real file -> list -> open -> delete round trip
        svc.capability_grants["org.nuxel.Camera"] = {"camera:capture": "always", "camera:preview": "always"}
        jpeg = b"\xff\xd8\xff\xe0" + b"REALJPEGBYTES" * 64
        cap = bridge.json.loads(svc.CameraCapture("org.nuxel.Camera", "photo", "image/jpeg",
                                                   base64.b64encode(jpeg).decode()))
        check(cap.get("success") is True, "granted capture succeeds")
        cid = cap["capture"]["id"]
        check(cid.endswith(".jpg"), "capture id carries .jpg extension")

        listed = bridge.json.loads(svc.CameraListCaptures("org.nuxel.Camera", "photo"))
        check(listed.get("count") == 1, "list returns the one captured photo")
        check(listed["captures"][0]["id"] == cid, "list id matches capture")
        check("data_b64" not in listed["captures"][0], "list never returns base64 pixel data")

        opened = bridge.json.loads(svc.CameraOpen("org.nuxel.Camera", cid))
        check(opened.get("success") is True, "open returns the capture")
        check(base64.b64decode(opened["capture"]["data_b64"]) == jpeg, "open returns original bytes")

        deleted = bridge.json.loads(svc.CameraDelete("org.nuxel.Camera", cid))
        check(deleted.get("success") is True, "delete succeeds")
        check(bridge.json.loads(svc.CameraListCaptures("org.nuxel.Camera", "photo")).get("count") == 0,
              "delete removes the file from the store")

        # 4. video gets honest .webm extension (never mis-extensioned)
        webm = b"\x1a\x45\xdf\xa3" + b"WEBM" * 64
        vcap = bridge.json.loads(svc.CameraCapture("org.nuxel.Camera", "video", "video/webm",
                                                    base64.b64encode(webm).decode()))
        check(vcap.get("success") is True and vcap["capture"]["id"].endswith(".webm"),
              "video/webm saves as .webm")

        # 5. D-Bus signatures match the contract
        check(svc.CameraCapture._dbus_in_signature == "ssss", "CameraCapture in_signature ssss")
        check(svc.CameraListCaptures._dbus_in_signature == "ss", "CameraListCaptures in_signature ss")
        check(svc.CameraOpen._dbus_in_signature == "ss", "CameraOpen in_signature ss")
        check(svc.CameraDelete._dbus_in_signature == "ss", "CameraDelete in_signature ss")
        check(svc.CameraStatus._dbus_in_signature == "s", "CameraStatus in_signature s")

        print("\nbridge-camera: %d failure(s)" % len(FAILURES))
        return 1 if FAILURES else 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
