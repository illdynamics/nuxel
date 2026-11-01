"""Compositor output transform backend for Nuxel orientation.

The S10+ compositor is Phoc/wlroots on a headless output.  The panel itself is
still portrait scanout, so a compositor transform is only half of the display
path: ``nuxel-wl-fb`` reads the transform from this module's published state and
rotates the captured landscape frame back into portrait scanout.

This module never guesses that a command succeeded.  After wlr-randr returns it
queries the output again and reports the transform the compositor actually
reports.  A missing utility, a missing output, or an unchanged transform is an
honest ``applied=False`` result.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

TRANSFORM_VALUES = ("normal", "90", "180", "270", "flipped",
                    "flipped-90", "flipped-180", "flipped-270")
QUARTER_TURNS = {"normal": 0, "90": 90, "180": 180, "270": 270}

DEFAULT_RUNTIME_DIR = "/run/nuxel-wayland"
DEFAULT_WAYLAND_DISPLAY = "wayland-0"


def _comp(config=None):
    return (config or {}).get("compositor", {})


def _run_env(config=None):
    comp = _comp(config)
    env = dict(os.environ)
    # The compositor owns a root-only runtime dir on the phone.  Never inherit a
    # stale desktop WAYLAND_DISPLAY from a shell; the orientation document is
    # the single source for this stack.
    env["XDG_RUNTIME_DIR"] = comp.get("runtime_dir", DEFAULT_RUNTIME_DIR)
    env["WAYLAND_DISPLAY"] = comp.get("wayland_display", DEFAULT_WAYLAND_DISPLAY)
    return env


def scale_for(degrees, config=None):
    """Physical scale that yields a real logical desktop for the pose.

    PWNAGE-54000 live measurement on HEADLESS-1:
      * portrait pose, transform normal/180, scale 2 -> 360x760 logical;
      * landscape pose, transform 90/270, scale 1 -> 1520x720 logical.
    Scale 2 in landscape would keep the logical desktop at 760x360 and made
    VNC report 720x1520 even though the pixels were rotated.  The scale is part
    of the orientation transaction, not a separate cosmetic setting.
    """
    comp = _comp(config)
    if int(degrees) in (90, 270):
        try:
            return float(comp.get("landscape_scale", 1))
        except (TypeError, ValueError):
            return 1.0
    try:
        return float(comp.get("portrait_scale", 2))
    except (TypeError, ValueError):
        return 2.0


def transform_for(degrees, config=None):
    """Return the compositor transform string for an effective orientation.

    The mapping is deliberately data-driven because the physical direction has
    to be calibrated on the handset.  The shipped document starts with the
    inverse-pose candidate and keeps ``transform_map_verified=false`` until the
    owner confirms it.
    """
    comp = _comp(config)
    mapping = comp.get("transform_map", {"0": "normal", "90": "270",
                                          "180": "180", "270": "90"})
    return mapping.get(str(degrees), mapping.get(degrees))


def wlr_randr_available():
    """True when the ``wlr-randr`` executable is on PATH.

    ``command`` is a shell builtin, not an executable; the previous
    ``subprocess.run(["command", "-v", ...])`` therefore always failed.
    """
    return shutil.which("wlr-randr") is not None


def _parse_json_outputs(raw):
    try:
        doc = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("wlr-randr returned invalid JSON: %s" % exc)
    return doc if isinstance(doc, list) else []


def _select_output(outputs, wanted):
    enabled = [o for o in outputs if isinstance(o, dict) and o.get("enabled", True)]
    if not enabled:
        return None
    if wanted and wanted != "auto":
        for out in enabled:
            if out.get("name") == wanted:
                return out
        return None
    # The live output is whichever enabled output the compositor currently
    # exports.  Prefer an actual panel-looking name, then the first output.
    for out in enabled:
        if str(out.get("name", "")).startswith(("DSI-", "eDP-", "LVDS-")):
            return out
    return enabled[0]


def output_status(config=None, output=None):
    """Query the live output and return dimensions/transform truth.

    ``logical_width/height`` account for the compositor transform.  The
    physical mode stays the reported output mode; ``nuxel-wl-fb`` handles the
    final scanout rotation.
    """
    comp = _comp(config)
    wanted = output or comp.get("output", "auto")
    if not wlr_randr_available():
        return {
            "backend": "none", "output": None, "transform": None,
            "applied": False, "error": "wlr-randr not present",
            "outputs": [],
        }
    try:
        proc = subprocess.run(
            ["wlr-randr", "--json"], capture_output=True, text=True,
            timeout=5, env=_run_env(config))
    except (OSError, subprocess.SubprocessError) as exc:
        return {"backend": "wlr-randr", "output": wanted, "transform": None,
                "applied": False, "error": str(exc), "outputs": []}
    if proc.returncode != 0:
        return {"backend": "wlr-randr", "output": wanted, "transform": None,
                "applied": False,
                "error": proc.stderr.strip() or "wlr-randr query failed",
                "outputs": []}
    try:
        outputs = _parse_json_outputs(proc.stdout)
    except RuntimeError as exc:
        return {"backend": "wlr-randr", "output": wanted, "transform": None,
                "applied": False, "error": str(exc), "outputs": []}
    out = _select_output(outputs, wanted)
    if out is None:
        names = [o.get("name") for o in outputs if isinstance(o, dict)]
        want = "the configured output %r" % wanted if wanted != "auto" else "any enabled output"
        return {"backend": "wlr-randr", "output": wanted, "transform": None,
                "applied": False, "outputs": names,
                "error": "no enabled output matching %s (compositor has %s)"
                         % (want, ", ".join(str(n) for n in names) or "none")}
    current = None
    for mode in out.get("modes", []):
        if mode.get("current"):
            current = mode
            break
    if current is None and out.get("modes"):
        current = out["modes"][0]
    width = int((current or {}).get("width") or 0)
    height = int((current or {}).get("height") or 0)
    transform = out.get("transform", "normal")
    quarter = QUARTER_TURNS.get(transform, 0)
    try:
        scale = float(out.get("scale") or 1.0)
    except (TypeError, ValueError):
        scale = 1.0
    if scale <= 0:
        scale = 1.0
    # wlroots logical geometry = scanout mode / scale, then swapped by a
    # quarter-turn transform.  The physical panel mode is intentionally unchanged.
    logical_w = int(round(width / scale))
    logical_h = int(round(height / scale))
    if quarter in (90, 270):
        logical_w, logical_h = logical_h, logical_w
    return {
        "backend": "wlr-randr",
        "output": out.get("name"),
        "transform": transform,
        "physical_width": width,
        "physical_height": height,
        "logical_width": logical_w,
        "logical_height": logical_h,
        "scale": scale,
        "enabled": bool(out.get("enabled", True)),
        "applied": True,
        "error": "",
        "outputs": [o.get("name") for o in outputs if isinstance(o, dict)],
    }


def apply_transform(degrees, config=None, dry_run=False, output=None):
    """Apply an effective orientation and verify the compositor accepted it.

    Returns an honest result including the output queried *after* the change.
    ``applied=True`` only when the live compositor reports the requested
    transform for the live output.
    """
    comp = _comp(config)
    transform = transform_for(degrees, config)
    if transform not in TRANSFORM_VALUES:
        return {"applied": False, "backend": "wlr-randr", "output": output,
                "transform": transform, "error": "no transform mapped for %r" % (degrees,),
                "dry_run": dry_run}
    before = output_status(config, output)
    target = output or before.get("output") or comp.get("output", "auto")
    if dry_run:
        return {"applied": False, "backend": "wlr-randr", "output": target,
                "transform": transform, "requested_transform": transform,
                "error": "", "dry_run": True, "before": before}
    if not wlr_randr_available():
        return {"applied": False, "backend": "wlr-randr", "output": target,
                "transform": transform, "error": "wlr-randr not present",
                "dry_run": False, "before": before}
    if before.get("output") is None:
        return {"applied": False, "backend": "wlr-randr", "output": target,
                "transform": transform, "error": before.get("error") or "output unavailable",
                "dry_run": False, "before": before}
    target = before["output"]
    try:
        scale_value = scale_for(degrees, config)
        proc = subprocess.run(
            ["wlr-randr", "--output", target, "--transform", transform,
             "--scale", ("%g" % scale_value)],
            capture_output=True, text=True, timeout=5, env=_run_env(config))
    except (OSError, subprocess.SubprocessError) as exc:
        return {"applied": False, "backend": "wlr-randr", "output": target,
                "transform": transform, "error": str(exc), "dry_run": False,
                "before": before}
    after = output_status(config, target)
    scale_ok = False
    try:
        scale_ok = abs(float(after.get("scale") or 0) - scale_value) < 0.001
    except (TypeError, ValueError):
        scale_ok = False
    applied = bool(proc.returncode == 0 and after.get("output") == target
                   and after.get("transform") == transform and scale_ok)
    err = proc.stderr.strip()
    if proc.returncode != 0 and not err:
        err = "wlr-randr exited %d" % proc.returncode
    elif not applied:
        err = ("compositor did not report %s (reported %r)"
               % (transform, after.get("transform")))
    try:
        after_scale = float(after.get("scale") or 1.0)
    except (TypeError, ValueError):
        after_scale = 1.0
    if after_scale <= 0:
        after_scale = 1.0
    expected_w = int(round((after.get("physical_width") or 0) / after_scale))
    expected_h = int(round((after.get("physical_height") or 0) / after_scale))
    quarter = QUARTER_TURNS.get(transform, 0)
    if quarter in (90, 270):
        expected_w, expected_h = expected_h, expected_w
    geometry = (after.get("logical_width"), after.get("logical_height"))
    geometry_ok = bool(applied and geometry == (expected_w, expected_h))
    if applied and not geometry_ok:
        applied = False
        err = ("logical geometry not verified: expected %sx%s, got %sx%s"
               % (expected_w, expected_h, geometry[0], geometry[1]))
    result = {
        "applied": applied,
        "display_verified": bool(applied and geometry_ok),
        "geometry_verified": geometry_ok,
        "backend": "wlr-randr",
        "output": target,
        "transform": transform,
        "requested_transform": transform,
        "requested_scale": scale_value,
        "physical_width": after.get("physical_width"),
        "physical_height": after.get("physical_height"),
        "logical_width": after.get("logical_width"),
        "logical_height": after.get("logical_height"),
        "expected_logical_width": expected_w,
        "expected_logical_height": expected_h,
        "scale": after.get("scale"),
        "error": "" if applied else err,
        "dry_run": False,
        "before": before,
        "after": after,
    }
    return result
