#!/usr/bin/env python3
"""Regression test: the notification hub bounds application hints.

Measured defect (PWNAGE-99000): ZapZap supplied 2.8 MB `image-data` hints,
which bloated the durable store to 19 MB and made the hub emit multi-megabyte
D-Bus signals.  The hub must truncate hints at the boundary, not persist them.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "notifications.py")
spec = importlib.util.spec_from_file_location("nuxel_notifications", SRC)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception as exc:  # host without dbus/gi
    print("SKIP notification hub import unavailable: %s" % exc)
    sys.exit(0)

huge = {"image-data": "x" * 2_800_000, "desktop-entry": "zapzap"}
bounded = mod._bounded_hints(huge)
assert bounded.get("nuxel.hints_truncated") is True
assert bounded.get("nuxel.hints_bytes") == len(json.dumps(huge))
assert len(json.dumps(bounded)) < 4096

small = {"a": 1, "b": "two"}
assert mod._bounded_hints(small) == small
assert mod._bounded_hints(None) == {}
print("ALL PASS notification hints are bounded")
