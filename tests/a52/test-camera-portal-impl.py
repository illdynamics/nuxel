#!/usr/bin/env python3
"""Offline tests: standard XDG camera portal backend + fail-closed privacy.

The standard org.freedesktop.portal.Camera is served by xdg-desktop-portal,
which routes to an impl backend (org.freedesktop.impl.portal.Camera). The
private org.nuxel.Camera broker is a different service and must stay separate.
These tests never touch hardware; they prove discovery, the standard method
surface, the .portal/D-Bus wiring and that a missing/corrupt privacy file
cannot unblock the camera.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
IMPL = os.path.join(ROOT, "shell", "nuxel-camera-portal", "nuxel_camera_portal_impl.py")
PRIVACY = os.path.join(ROOT, "services", "nuxel-bridge", "src", "privacy_provider.py")

FAILURES: list = []


def check(cond, msg, detail=""):
    print(("  OK   " if cond else "  FAIL ") + msg + ("" if cond or not detail else " — " + detail))
    if not cond:
        FAILURES.append(msg)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    impl = load(IMPL, "nuxel_camera_impl")
    src = open(IMPL).read()

    check(impl.BUS_NAME == "org.freedesktop.impl.portal.desktop.nuxel", "impl backend bus name is the nuxel impl name")
    check(impl.IFACE == "org.freedesktop.impl.portal.Camera", "impl interface is org.freedesktop.impl.portal.Camera")
    # A comment may NAME the public portal; no string literal may assign/claim it.
    check('"org.freedesktop.portal.Camera"' not in src and "'org.freedesktop.portal.Camera'" not in src,
          "impl never claims the public portal name")

    # discovery: only exynos-fimc-is nodes count; /dev/video0/V4L2 webcams do not
    d = tempfile.mkdtemp()
    for name, content in (("video0", "uvcvideo\n"), ("video130", "exynos-fimc-is-i0p\n"),
                          ("video131", "exynos-fimc-is-i0c\n")):
        os.makedirs(os.path.join(d, name))
        open(os.path.join(d, name, "name"), "w").write(content)
    nodes = impl.discover_fimc_capture_nodes(d)
    check([n["node"] for n in nodes] == ["/dev/video130", "/dev/video131"],
          "only exynos-fimc-is nodes are discovered (never /dev/video0)", json.dumps(nodes))
    check(impl.discover_fimc_capture_nodes(os.path.join(d, "missing")) == [], "missing sysfs => no nodes")

    os.environ.pop("NUXEL_PIPEWIRE_REMOTE", None)
    os.environ.pop("XDG_RUNTIME_DIR", None)
    check(impl.pipewire_remote_path() is None, "no pipewire socket => no remote (is_camera_present false)")

    # methods present in source, matching the implementation contract
    for m in ("AccessCamera", "OpenPipeWireRemote", "IsCameraPresent", "version"):
        check(m in src, "impl implements %s" % m)
    check('in_signature="osa{sv}"' in src and 'out_signature="ua{sv}"' in src,
          "AccessCamera has the impl signature (o handle, s app_id, a{sv} options) -> (u, a{sv})")
    check('out_signature="ha{sv}"' in src, "OpenPipeWireRemote returns an fd (h)")

    # grant check fails closed
    old = impl.PERMISSIONS_DIR
    impl.PERMISSIONS_DIR = tempfile.mkdtemp()
    os.environ.pop("NUXEL_CAMERA_IMPL_SELFTEST_ALLOW", None)
    check(impl._granted("org.example.App") is False, "missing grant file => denied")
    grants = os.path.join(impl.PERMISSIONS_DIR, "org.example.App.json")
    open(grants, "w").write("{not json")
    check(impl._granted("org.example.App") is False, "corrupt grant file => denied")
    open(grants, "w").write(json.dumps({"camera": {"granted": True, "duration": "always"}}))
    check(impl._granted("org.example.App") is True, "explicit camera grant => granted")
    open(grants, "w").write(json.dumps({"camera": {"granted": True, "duration": "revoked"}}))
    check(impl._granted("org.example.App") is False, "revoked grant => denied")
    impl.PERMISSIONS_DIR = old

    # portal wiring files exist and route Camera to the nuxel impl
    portal_file = os.path.join(ROOT, "shell/nuxel-camera-portal/xdg-desktop-portal/nuxel-camera.portal")
    dbus_file = os.path.join(ROOT, "shell/nuxel-camera-portal/dbus/org.freedesktop.impl.portal.desktop.nuxel-camera.service")
    unit = os.path.join(ROOT, "shell/nuxel-camera-portal/systemd/nuxel-camera-portal-impl.service")
    for f in (portal_file, dbus_file, unit):
        check(os.path.isfile(f), "portal wiring file exists: %s" % os.path.relpath(f, ROOT))
    if os.path.isfile(portal_file):
        txt = open(portal_file).read()
        check("Interfaces=org.freedesktop.impl.portal.Camera" in txt and "UseIn=Nuxel" in txt,
              ".portal advertises impl.portal.Camera for Nuxel")
    if os.path.isfile(dbus_file):
        txt = open(dbus_file).read()
        check("Exec=/usr/libexec/nuxel/nuxel-camera-portal-impl" in txt, "D-Bus activation exec is the impl")
    conf = open(os.path.join(ROOT, "configs/nuxel/portals.conf")).read()
    check("org.freedesktop.impl.portal.Camera=nuxel" in conf, "portals.conf routes Camera to the nuxel impl")

    # privacy fail-closed
    os.environ["NUXEL_PRIVACY_DIR"] = tempfile.mkdtemp()
    privacy = load(PRIVACY, "nuxel_privacy_provider")
    d2 = tempfile.mkdtemp()
    privacy.CAMERA_DOC = os.path.join(d2, "camera.json")
    check(privacy.camera_capture_blocked() is True, "missing privacy file => camera blocked (fail closed)")
    open(privacy.CAMERA_DOC, "w").write('{"blocked": false}')
    check(privacy.camera_capture_blocked() is False, "explicit blocked=false => unblocked")
    open(privacy.CAMERA_DOC, "w").write("{broken")
    check(privacy.camera_capture_blocked() is True, "corrupt privacy file => camera blocked")
    open(privacy.CAMERA_DOC, "w").write('{"blocked": "false"}')
    check(privacy.camera_capture_blocked() is True, "non-boolean blocked => camera blocked")

    print()
    if FAILURES:
        print("%d CHECK(S) FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks PASS — portal impl + fail-closed privacy (OFFLINE_TESTED)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
