#!/usr/bin/env python3
"""Offline tests for the A49 USB-C/DP and wireless-cast capability probes.

Both probes are READ-ONLY: they enumerate real evidence and produce an honest
verdict. These tests build fixture trees and run the REAL scripts against them
(NUXEL_DIAG_ROOT / PATH), so a verdict is the actual code path, not a
re-implementation. Physical HDMI output and a moving casted picture remain
NEEDS_OWNER_TEST and are never simulated here.
"""

import json
import os
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TYPEC = os.path.join(HERE, "..", "..", "nuxel-typec-diag.sh")
CAST = os.path.join(HERE, "..", "..", "nuxel-cast-diag.sh")


def run_tool(tool, root, env=None):
    e = {"NUXEL_DIAG_ROOT": root, "PATH": os.environ.get("PATH", "")}
    if env:
        e.update(env)
    r = subprocess.run(["bash", tool, "status", "--json"],
                       capture_output=True, text=True, env=e)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def mkbin(root, name, output):
    path = os.path.join(root, "bin", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("#!/bin/sh\n%s\n" % output)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


# ---- Type-C / DP -----------------------------------------------------------

def test_typec_dp_active(tmp_path):
    root = str(tmp_path)
    write(os.path.join(root, "sys/class/typec/port0/data_role"), "device")
    write(os.path.join(root, "sys/class/typec/port0/port0-altmode/displayport/status"), "enabled")
    write(os.path.join(root, "sys/class/drm/card0-DP-1/status"), "connected")
    doc = run_tool(TYPEC, root)
    assert doc["verdict"] == "DP_ALT_MODE_ACTIVE"
    assert doc["read_only"] is True


def test_typec_dp_negotiated_no_connector(tmp_path):
    root = str(tmp_path)
    write(os.path.join(root, "sys/class/typec/port0/port0-altmode/displayport/status"), "enabled")
    write(os.path.join(root, "sys/class/drm/card0-DP-1/status"), "disconnected")
    doc = run_tool(TYPEC, root)
    assert doc["verdict"] == "TYPEC_DP_NEGOTIATED"


def test_typec_enumerated_no_dp(tmp_path):
    root = str(tmp_path)
    write(os.path.join(root, "sys/class/typec/port0/data_role"), "device")
    doc = run_tool(TYPEC, root)
    assert doc["verdict"] == "TYPEC_ENUMERATED_NO_DP"


def test_typec_none(tmp_path):
    root = str(tmp_path)
    doc = run_tool(TYPEC, root)
    assert doc["verdict"] == "NO_TYPEC_NO_DRM"


# ---- Wireless cast ---------------------------------------------------------

WLR_SCREENCOPY = ("usr/share/wayland-protocols/unstable/wlr-screencopy/"
                  "wlr-screencopy-unstable-v1.xml")


def test_cast_miracast_candidate(tmp_path):
    root = str(tmp_path)
    mkbin(root, "iw", 'echo "Supported interface modes:"; echo "  * P2P-client"')
    mkbin(root, "grim", "exit 0")
    mkbin(root, "gst-inspect-1.0", "echo openh264enc")
    write(os.path.join(root, WLR_SCREENCOPY), "<protocol/>")
    doc = run_tool(CAST, root, env={"PATH": os.path.join(root, "bin") + ":" + os.environ["PATH"]})
    assert doc["verdict"] == "MIRACAST_CANDIDATE"
    assert "openh264enc" in doc["encoders"]


def test_cast_lan_share_no_p2p(tmp_path):
    root = str(tmp_path)
    mkbin(root, "grim", "exit 0")
    mkbin(root, "gst-inspect-1.0", "echo x264enc")
    write(os.path.join(root, WLR_SCREENCOPY), "<protocol/>")
    doc = run_tool(CAST, root, env={"PATH": os.path.join(root, "bin") + ":" + os.environ["PATH"]})
    assert doc["verdict"] == "LAN_SCREENSHARE_CANDIDATE"


def test_cast_no_capture(tmp_path):
    root = str(tmp_path)
    mkbin(root, "iw", 'echo "  * P2P-client"')
    mkbin(root, "gst-inspect-1.0", "echo openh264enc")
    doc = run_tool(CAST, root, env={"PATH": os.path.join(root, "bin") + ":" + os.environ["PATH"]})
    assert doc["verdict"] == "NO_CAPTURE"
