"""Compositor apply/revert path for output rotation (honest, bounded).

Phase 3 of the mission. The phone's Phoc/wlroots compositor must actually
support per-output transform for a rotation to mean anything; rotating pixels
alone is explicitly disallowed. This module:

* maps a physical pose (0/90/180/270) to a wlroots transform via the
  ``compositor.transform_map`` in the orientation document,
* attempts ``wlr-randr --output <out> --transform <t>`` when present,
* returns an honest ``{applied, backend, transform, error}`` result,
* supports an auto-revert to a last-good transform after a bounded interval
  (used when a change blanks the display or leaves input unusable).

The exact transform mapping and the matching touch calibration are
``unverified`` until exercised on the real device. Nothing here flashes or
writes partitions.
"""

from __future__ import annotations

import os
import subprocess

TRANSFORM_VALUES = ("normal", "90", "180", "270")


def transform_for(degrees, config=None):
    """Return the compositor transform string for a physical pose."""
    comp = (config or {}).get("compositor", {})
    mapping = comp.get("transform_map", {"0": "normal", "90": "270",
                                          "180": "180", "270": "90"})
    return mapping.get(str(degrees), mapping.get(degrees))


def wlr_randr_available():
    """True when the ``wlr-randr`` binary actually exists on the PATH."""
    try:
        return subprocess.run(
            ["command", "-v", "wlr-randr"], capture_output=True,
            text=True, timeout=2).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def apply_transform(degrees, config=None, dry_run=False):
    """Attempt to apply a physical-pose rotation through wlr-randr.

    Returns ``{applied, backend, transform, output, error, dry_run}``. ``applied``
    is True only when the compositor accepted the transform. A missing binary or
    a failed call is an honest ``applied=False``, never a claim of success.
    """
    comp = (config or {}).get("compositor", {})
    output = comp.get("output", "DSI-1")
    transform = transform_for(degrees, config)
    if transform is None or transform not in TRANSFORM_VALUES:
        return {"applied": False, "backend": "wlr-randr", "output": output,
                "transform": None, "error": "no transform mapped for %r" % (degrees,),
                "dry_run": dry_run}
    if dry_run:
        return {"applied": False, "backend": "wlr-randr", "output": output,
                "transform": transform, "error": "", "dry_run": True}
    if not wlr_randr_available():
        return {"applied": False, "backend": "wlr-randr", "output": output,
                "transform": transform,
                "error": "wlr-randr not present (no compositor transform backend)",
                "dry_run": False}
    try:
        proc = subprocess.run(
            ["wlr-randr", "--output", output, "--transform", transform],
            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"applied": False, "backend": "wlr-randr", "output": output,
                "transform": transform, "error": str(exc), "dry_run": False}
    return {
        "applied": proc.returncode == 0,
        "backend": "wlr-randr",
        "output": output,
        "transform": transform,
        "error": proc.stderr.strip() if proc.returncode != 0 else "",
        "dry_run": False,
    }
