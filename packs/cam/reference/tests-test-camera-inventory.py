#!/usr/bin/env python3
"""Offline unit tests: camera policy/hardware inventory honesty (A52).

Guards that the shipped camera policy records the observed beyond2lte sensors
(front main = s5k3j1, not the historical s5k2l4sx guess), marks firmware
candidates as hints (never observations), and keeps the private broker contract
consistent with the renamed portal.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
POLICY = os.path.join(ROOT, "configs", "nuxel", "camera", "camera.json")

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def main() -> int:
    pol = json.load(open(POLICY))

    front = [s["name"] for s in pol["device"]["expected_sensors"]["front"]]
    check("s5k3j1" in front and "s5k2l4sx_front" not in " ".join(front),
          "front main sensor is recorded as s5k3j1 (observed), not the s5k2l4sx guess")
    rear = [s["name"] for s in pol["device"]["expected_sensors"]["rear"]]
    check(set(rear) == {"s5k2l4", "s5k3m3", "s5k3p9"}, "three rear sensors recorded")

    check(pol["device"].get("comment_expected", ""), "expected-shipped hardware is labelled, not observation")
    check("never" in pol.get("comment", "").lower() or "no frame is ever claimed" in pol.get("comment", "").lower(),
          "policy states the no-fabrication rule")

    check(pol["pipeline"]["portal"]["interface"] == "org.nuxel.Camera",
          "portal interface is the private org.nuxel.Camera")
    check(pol["pipeline"]["portal"]["synthetic_when_no_hardware"]["enabled"] is False,
          "synthetic source is opt-in, never the device default")

    check(pol["diagnostics"]["require_explicit_yes_for_capture"] is True
          and pol["diagnostics"]["auto_capture_on_boot"] is False,
          "capture is owner-initiated only, never automatic")

    print("\ncamera-inventory: %d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
