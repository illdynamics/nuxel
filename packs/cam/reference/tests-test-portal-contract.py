#!/usr/bin/env python3
"""Offline unit tests: private Nuxel camera broker contract (A52).

Guards the critical A52 fix: the Nuxel camera broker must NEVER claim the
standard ``org.freedesktop.portal.Camera`` bus name (which would collide with a
real xdg-desktop-portal backend and expose incompatible methods).  It is a
private ``org.nuxel.Camera`` broker with an honest ``IsCameraPresent`` and no
hard-coded synthetic default.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
PORTAL = os.path.join(ROOT, "shell", "nuxel-camera-portal", "nuxel_camera_portal.py")
UNIT = os.path.join(ROOT, "shell", "nuxel-camera-portal", "systemd", "nuxel-camera-portal.service")

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def main() -> int:
    src = open(PORTAL).read()
    unit = open(UNIT).read()

    check('DBUS_NAME = "org.nuxel.Camera"' in src, "bus name is the private org.nuxel.Camera")
    check('DBUS_NAME = "org.freedesktop.portal.Camera"' not in src
          and 'interface_name != "org.freedesktop.portal.Camera"' not in src,
          "no standard portal bus-name assignment or runtime check remains")
    check('DBUS_PATH = "/org/nuxel/Camera"' in src, "object path is private")
    check('<interface name="org.nuxel.Camera">' in src, "introspection interface is private")
    check('IsCameraPresent' in src, "IsCameraPresent method declared")
    check('_v4l2_nodes_present' in src, "honest V4L2 node presence helper exists")
    check('--test-source' in src, "synthetic source requires an explicit flag")
    # The standard portal API is deliberately absent (we are not implementing it
    # under a hijacked name): the broker must NOT export AccessCamera/OpenPipeWireRemote.
    check('AccessCamera' not in src and 'OpenPipeWireRemote' not in src,
          "broker does not fake the standard AccessCamera/OpenPipeWireRemote methods")

    check('--synthetic' not in unit.split('ExecStart=')[1].split('\n')[0],
          "systemd unit no longer hard-codes --synthetic")

    print("\nportal-contract: %d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
