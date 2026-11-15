#!/usr/bin/env python3
"""Nuxel standard XDG Camera portal backend (``org.freedesktop.impl.portal.Camera``).

This is the STANDARD freedesktop camera backend that ``xdg-desktop-portal``
routes ``org.freedesktop.portal.Camera`` to. It is a separate service from the
private ``org.nuxel.Camera`` broker (``nuxel-camera-portal``) and must never
claim that private name.

Contract (xdg-desktop-portal data/org.freedesktop.portal.Camera.xml and
desktop-portal/camera.c):

    AccessCamera(o handle, s app_id, a{sv} options) -> (u response, a{sv} results)
        The xdg-desktop-portal frontend creates the Request object and emits
        ``Response``; a backend only answers 0 = granted / 1 = cancelled /
        2 = other. Nuxel grants through the canonical ``camera`` permission
        (Permission Manager / consent), never implicitly.

    OpenPipeWireRemote(o handle, s app_id, a{sv} options) -> (h fd, a{sv} results)
        Returns a PipeWire remote fd when the caller has an active grant.
        The fd is opened from ``/run/nuxel-pipewire/pipewire-0`` (or
        ``$XDG_RUNTIME_DIR/pipewire-0``) owned by the session user.

    IsCameraPresent -> b
        True only when a real exynos-fimc-is capture node is discovered; a node
        name in sysfs is NOT proof of frames (that is measured with
        ``nuxel-fimc-capture --probe-only``).

    version -> u (1)

The backend never fabricates a camera: with no FIMC-IS node it reports
IsCameraPresent=false and refuses OpenPipeWireRemote.
"""
from __future__ import annotations

import json
import os
import sys

BUS_NAME = "org.freedesktop.impl.portal.desktop.nuxel"
OBJECT_PATH = "/org/freedesktop/portal/desktop"
IFACE = "org.freedesktop.impl.portal.Camera"
SERVICE_VERSION = "1"

PERMISSIONS_DIR = os.environ.get("NUXEL_PERMISSIONS_DIR", "/var/lib/nuxel/permissions")
PIPEWIRE_REMOTE_CANDIDATES = (
    "/run/nuxel-pipewire/pipewire-0",
    "/run/nuxel-wayland/pipewire-0",
)


def _log(message: str) -> None:
    sys.stderr.write("nuxel-camera-impl: %s\n" % message)
    sys.stderr.flush()


def discover_fimc_capture_nodes(sys_class: str = "/sys/class/video4linux"):
    """Return exynos-fimc-is capture nodes discovered from driver sysfs."""
    nodes = []
    try:
        entries = sorted(os.listdir(sys_class))
    except OSError:
        return nodes
    for entry in entries:
        if not entry.startswith("video"):
            continue
        try:
            with open(os.path.join(sys_class, entry, "name")) as fh:
                name = fh.read().strip()
        except OSError:
            continue
        if "fimc-is" in name:
            nodes.append({"node": "/dev/" + entry, "name": name})
    return nodes


def pipewire_remote_path():
    """Return a usable PipeWire remote socket path, or None."""
    override = os.environ.get("NUXEL_PIPEWIRE_REMOTE")
    candidates = (override,) if override else ()
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        candidates += (os.path.join(runtime, "pipewire-0"),)
    candidates += PIPEWIRE_REMOTE_CANDIDATES
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def camera_present():
    if not discover_fimc_capture_nodes():
        return False
    return pipewire_remote_path() is not None


def _granted(app_id: str) -> bool:
    """Return True only when the canonical camera permission is granted.

    The bridge owns the permission store; a missing bridge or an explicit
    deny both fail closed. NUXEL_CAMERA_IMPL_ALLOW (tests only) is honoured
    because this module is also exercised without D-Bus.
    """
    if os.environ.get("NUXEL_CAMERA_IMPL_SELFTEST_ALLOW") == "1":
        return True
    # The canonical permission store is owned by the bridge. Prefer its
    # CameraStatus(permission) view; if the bridge is absent, fall back to the
    # central permD helper (same store) so the portal and the apps cannot
    # disagree. Any error is a DENY - this path must fail closed.
    try:
        import dbus  # type: ignore
        bus = dbus.SessionBus()
        proxy = bus.get_object("org.nuxel.Bridge", "/org/nuxel/Bridge")
        status = json.loads(str(proxy.CameraStatus(app_id)))
        perm = status.get("permission") or {}
        return bool(perm.get("camera_capture_granted"))
    except Exception as exc:  # noqa: BLE001
        _log("bridge permission check unavailable for %r: %s" % (app_id, exc))
    try:
        # Canonical store: /var/lib/nuxel/permissions/<app>.json, the same file
        # the bridge's grant/revoke path writes. A plain file read keeps this
        # service independent of the bridge's Python module layout.
        safe = app_id.replace("/", "_").replace("..", "_")
        with open(os.path.join(PERMISSIONS_DIR, "%s.json" % safe)) as fh:
            grants = json.load(fh)
        entry = grants.get("camera") or {}
        if isinstance(entry, bool):
            return entry
        if isinstance(entry, dict):
            return bool(entry.get("granted")) and entry.get("duration") != "revoked"
        return False
    except Exception as exc:  # noqa: BLE001 - fail closed
        _log("permission check failed for %r: %s" % (app_id, exc))
        return False


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--once" in argv:
        print(json.dumps({
            "bus_name": BUS_NAME,
            "interface": IFACE,
            "version": SERVICE_VERSION,
            "is_camera_present": camera_present(),
            "fimc_nodes": discover_fimc_capture_nodes(),
            "pipewire_remote": pipewire_remote_path(),
        }))
        return 0
    if "--selftest" in argv:
        nodes = discover_fimc_capture_nodes()
        present = camera_present()
        print("fimc_nodes=%d present=%s pipewire=%s" % (len(nodes), present, pipewire_remote_path()))
        return 0 if nodes else 3
    if "--version" in argv:
        print("%s %s" % (BUS_NAME, SERVICE_VERSION))
        return 0

    import dbus
    import dbus.mainloop.glib
    import dbus.service
    from gi.repository import GLib

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    try:
        name = dbus.service.BusName(BUS_NAME, bus, do_not_queue=True)
    except dbus.exceptions.NameExistsException:
        _log("another instance owns %s" % BUS_NAME)
        return 0

    class CameraImpl(dbus.service.Object):
        @dbus.service.method(IFACE, in_signature="osa{sv}", out_signature="ua{sv}")
        def AccessCamera(self, handle, app_id, options):
            app_id = str(app_id)
            if not camera_present():
                _log("AccessCamera %s: NO_CAMERA" % app_id)
                return dbus.UInt32(2), dbus.Dictionary({"error": "no camera"}, signature="sv")
            if not _granted(app_id):
                _log("AccessCamera %s: denied (no camera grant)" % app_id)
                return dbus.UInt32(1), dbus.Dictionary({}, signature="sv")
            _log("AccessCamera %s: granted" % app_id)
            return dbus.UInt32(0), dbus.Dictionary({}, signature="sv")

        @dbus.service.method(IFACE, in_signature="osa{sv}", out_signature="ha{sv}")
        def OpenPipeWireRemote(self, handle, app_id, options):
            app_id = str(app_id)
            if not camera_present() or not _granted(app_id):
                raise dbus.exceptions.DBusException(
                    "camera access not granted", name="org.freedesktop.DBus.Error.AccessDenied")
            path = pipewire_remote_path()
            fd = os.open(path, os.O_RDWR | os.O_CLOEXEC)
            return dbus.types.UnixFd(fd), dbus.Dictionary({}, signature="sv")

        @dbus.service.method(IFACE, in_signature="", out_signature="b")
        def IsCameraPresent(self):
            return camera_present()

        @dbus.service.method(IFACE, in_signature="", out_signature="u")
        def version(self):
            return dbus.UInt32(int(SERVICE_VERSION))

    impl = CameraImpl(bus, OBJECT_PATH)
    _log("READY %s %s pid=%d present=%s" % (BUS_NAME, IFACE, os.getpid(), camera_present()))
    loop = GLib.MainLoop()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 2, loop.quit)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 15, loop.quit)
    try:
        loop.run()
    finally:
        del impl, name
    return 0


if __name__ == "__main__":
    sys.exit(main())
