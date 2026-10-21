"""Orientation policy + hysteresis state machine (pure, no I/O).

Seven named modes exactly:

    portrait            -> {0}
    reverse_portrait    -> {180}
    landscape           -> {90}
    reverse_landscape   -> {270}
    auto                -> {0, 90, 180, 270}
    auto_portrait       -> {0, 180}
    auto_landscape      -> {90, 270}

A mode is either *fixed* (one allowed orientation) or *auto* (more than one,
sensor-gated). The policy guarantees the effective orientation is always a
member of the selected mode's allowed set; on a mode switch into an auto mode
whose current orientation is disallowed, a legal orientation is chosen
immediately (last permitted orientation, else the sensor-consistent one, else
the mode's first entry). Manual/fixed modes work with no sensor at all.
"""

from __future__ import annotations

import time

ALL_ORIENTATIONS = (0, 90, 180, 270)

# The seven modes and their allowed orientation sets. Order is not significant
# except that SEVEN_MODES is the exhaustive, authoritative list.
SEVEN_MODES = {
    "portrait":          {"label": "Portrait",           "allowed": (0,)},
    "reverse_portrait":  {"label": "Reverse portrait",   "allowed": (180,)},
    "landscape":         {"label": "Landscape",          "allowed": (90,)},
    "reverse_landscape": {"label": "Reverse landscape",  "allowed": (270,)},
    "auto":              {"label": "Auto (all)",         "allowed": (0, 90, 180, 270)},
    "auto_portrait":     {"label": "Auto portrait",      "allowed": (0, 180)},
    "auto_landscape":    {"label": "Auto landscape",     "allowed": (90, 270)},
}

MODE_ORDER = [
    "portrait", "reverse_portrait", "landscape", "reverse_landscape",
    "auto", "auto_portrait", "auto_landscape",
]

DEFAULT_MODE = "portrait"


class PolicyError(ValueError):
    """A mode or orientation value that cannot be interpreted."""


def validate_mode(mode):
    """Return ``mode`` if it is one of the seven names, else raise PolicyError."""
    if not isinstance(mode, str) or mode not in SEVEN_MODES:
        raise PolicyError("unknown orientation mode: %r (expected one of %s)"
                          % (mode, ", ".join(MODE_ORDER)))
    return mode


def validate_orientation(degrees):
    """Return ``degrees`` if it is a legal discrete orientation."""
    if degrees not in ALL_ORIENTATIONS:
        raise PolicyError("orientation must be 0/90/180/270, got %r" % (degrees,))
    return degrees


def is_auto(mode):
    """True when the mode is sensor-gated (has more than one allowed pose)."""
    return len(SEVEN_MODES[validate_mode(mode)]["allowed"]) > 1


def allowed_orientations(mode):
    """The immutable tuple of allowed discrete orientations for ``mode``."""
    return SEVEN_MODES[validate_mode(mode)]["allowed"]


def mode_from_document(doc, default=DEFAULT_MODE):
    """Read the selected mode from a config/state document, never raising.

    An absent/garbage mode falls back to ``default`` (portrait) because portrait
    is the documented safe initial default.
    """
    try:
        return validate_mode(doc.get("mode", default))
    except (PolicyError, AttributeError, TypeError):
        return default


def choose_initial_orientation(mode, last_orientation, sensor_orientation=None):
    """Choose a legal initial orientation immediately after a mode switch.

    * fixed mode        -> its single allowed orientation
    * auto mode         -> ``last_orientation`` when it is still legal,
                           else ``sensor_orientation`` when legal,
                           else the mode's first allowed orientation.

    This guarantees the effective orientation never sits outside the selected
    allowed set, even on the very first sample.
    """
    allowed = allowed_orientations(mode)
    if len(allowed) == 1:
        return allowed[0]
    if last_orientation in allowed:
        return last_orientation
    if sensor_orientation in allowed:
        return sensor_orientation
    return allowed[0]


def normalize_mode(doc):
    """Return a validated (mode, effective, last) triple from a document.

    Keeps ``effective`` inside the selected mode's allowed set even if the
    persisted document is stale/corrupt.
    """
    if not isinstance(doc, dict):
        doc = {}
    mode = mode_from_document(doc)
    last = doc.get("last_orientation")
    last = last if last in ALL_ORIENTATIONS else None
    eff = doc.get("effective_orientation")
    eff = eff if eff in ALL_ORIENTATIONS else None
    effective = eff if eff in allowed_orientations(mode) else choose_initial_orientation(mode, last)
    return mode, effective, last


class Orientator:
    """Hysteresis-bounded orientation state machine driven by gravity vectors.

    Consumes display-native gravity vectors ``(gx, gy, gz)`` (m/s^2, already
    rotated through the mount matrix) plus the selected ``mode``, and returns a
    new effective orientation only when a stable, unambiguous, allowed pose is
    held for the configured hysteresis window. Flat (|gz| dominates) and weak
    (|g| far from 1 g) samples are rejected; the last good orientation is
    preserved on flat per policy.
    """

    def __init__(self, mode=DEFAULT_MODE, config=None):
        cfg = config or {}
        self.policy_cfg = cfg.get("policy", cfg)
        self.hysteresis_ms = int(self.policy_cfg.get("hysteresis_ms", 450))
        self.cooldown_ms = int(self.policy_cfg.get("cooldown_ms", 250))
        self.debounce_ms = int(self.policy_cfg.get("debounce_ms", 60))
        self.flat_ratio = float(self.policy_cfg.get("flat_gravity_ratio", 0.55))
        self.weak_ms2 = float(self.policy_cfg.get("weak_gravity_ms2", 2.0))
        self.keep_last_on_flat = bool(self.policy_cfg.get("last_good_on_flat", True))
        # gravity reference vectors (display-native) per orientation
        self.reference = self._references(cfg.get("sensor", {}).get("gravity_reference", {}))
        self.mode = validate_mode(mode)
        self.current = choose_initial_orientation(self.mode, None)
        self._candidate = None
        self._candidate_since = None
        self._last_change = None
        self._last_sample = None

    @staticmethod
    def _references(grav_ref):
        refs = {}
        for key in ("0", "90", "180", "270"):
            v = grav_ref.get(key)
            if isinstance(v, (list, tuple)) and len(v) == 3:
                refs[int(key)] = tuple(float(x) for x in v)
        # Defaults when the document is absent (still calibration-unverified).
        refs.setdefault(0, (0.0, -1.0, 0.0))
        refs.setdefault(90, (1.0, 0.0, 0.0))
        refs.setdefault(180, (0.0, 1.0, 0.0))
        refs.setdefault(270, (-1.0, 0.0, 0.0))
        return refs

    # -- configuration -------------------------------------------------------
    def set_mode(self, mode, sensor_orientation=None):
        """Switch the selected policy; pick a legal effective orientation now."""
        self.mode = validate_mode(mode)
        self.current = choose_initial_orientation(
            self.mode, self.current, sensor_orientation)
        self._candidate = None
        self._candidate_since = None
        return self.current

    # -- classification -------------------------------------------------------
    def classify(self, gravity):
        """Return (orientation, quality) from one display-native gravity vector.

        ``orientation`` is one of 0/90/180/270; ``quality`` is 'flat', 'weak',
        or 'good'. A flat/weak sample has ``orientation`` equal to the nearest
        reference but must NOT drive a rotation.
        """
        gx, gy, gz = (float(x) for x in gravity)
        magnitude = (gx * gx + gy * gy + gz * gz) ** 0.5
        if magnitude < self.weak_ms2:
            return self._nearest(gx, gy, gz), "weak"
        flat = abs(gz) / magnitude
        if flat > self.flat_ratio:
            return self._nearest(gx, gy, gz), "flat"
        return self._nearest(gx, gy, gz), "good"

    def _nearest(self, gx, gy, gz):
        mag = (gx * gx + gy * gy + gz * gz) ** 0.5 or 1.0
        best, best_dot = 0, -2.0
        for deg, (rx, ry, rz) in sorted(self.reference.items()):
            dot = (gx * rx + gy * ry + gz * rz) / mag
            if dot > best_dot:
                best_dot, best = dot, deg
        return best

    # -- event loop -----------------------------------------------------------
    def update(self, gravity, now=None):
        """Feed one gravity sample; return the new effective orientation or None.

        ``None`` means "no rotation this tick" (still settling, flat, weak,
        cooldown, or the candidate is disallowed). Fixed modes always return
        None: their orientation cannot be changed by a sensor.
        """
        now = now if now is not None else time.monotonic()
        if not is_auto(self.mode):
            return None
        orient, quality = self.classify(gravity)
        # Flat/weak never rotate; preserve the last good orientation.
        if quality != "good":
            self._candidate = None
            self._candidate_since = None
            self._last_sample = now
            return None
        if self._last_change is not None and (now - self._last_change) * 1000 < self.cooldown_ms:
            self._last_sample = now
            return None
        if orient not in allowed_orientations(self.mode):
            self._candidate = None
            self._candidate_since = None
            self._last_sample = now
            return None
        if orient == self.current:
            self._candidate = None
            self._candidate_since = None
            self._last_sample = now
            return None
        # First sight of a different allowed candidate: start the window.
        if self._candidate != orient:
            self._candidate = orient
            self._candidate_since = now
            self._last_sample = now
            return None
        if (now - self._candidate_since) * 1000 < self.hysteresis_ms:
            self._last_sample = now
            return None
        # Candidate held for the hysteresis window -> commit.
        self.current = orient
        self._candidate = None
        self._candidate_since = None
        self._last_change = now
        self._last_sample = now
        return orient

    def status(self):
        return {
            "mode": self.mode,
            "auto": is_auto(self.mode),
            "effective_orientation": self.current,
            "allowed": list(allowed_orientations(self.mode)),
        }
