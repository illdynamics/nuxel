"""Sensor decoding for orientation (no writes, no daemons).

Decodes a VERIFIED sensor source into a display-native gravity vector. Two real
sources are supported behind a common interface:

* ``IIOAccelSource`` — raw IIO accelerometer channels read straight from sysfs.
* ``SensorProxySource`` — iio-sensor-proxy's ``net.hadess.SensorProxy`` D-Bus
  service (``HasAccelerometer`` / ``AccelerometerOrientation``).

The mount matrix is applied in :func:`apply_mount_matrix`. The exact matrix and
gravity convention are ``calibration_status=unverified`` until an owner tilts
the handset and confirms the mapping — this module never fabricates a reading.
"""

from __future__ import annotations

import glob
import os

# 1 g in m/s^2 — the standard-gravity magnitude used to normalise a raw vector.
G_MS2 = 9.80665


def apply_mount_matrix(reading, matrix):
    """Map a sensor-axes vector ``(x, y, z)`` through a 3x3 row-major matrix.

    Returns the display-native vector ``(x', y', z')``. An absent/short matrix
    falls back to the identity, which is safe (still ``unverified``) but never
    a silent guess about the real hardware mounting.
    """
    if not isinstance(matrix, (list, tuple)) or len(matrix) != 9:
        matrix = (1, 0, 0, 0, 1, 0, 0, 0, 1)
    x, y, z = (float(v) for v in reading)
    m = [float(v) for v in matrix]
    nx = m[0] * x + m[1] * y + m[2] * z
    ny = m[3] * x + m[4] * y + m[5] * z
    nz = m[6] * x + m[7] * y + m[8] * z
    return (nx, ny, nz)


def gravity_magnitude(vec):
    return (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5


class SourceUnavailable(Exception):
    """The sensor source exists as a concept but cannot produce a reading now."""


class SensorReading:
    """One display-native gravity sample plus its provenance."""

    __slots__ = ("x", "y", "z", "source", "available", "reason")

    def __init__(self, x, y, z, source="unknown", available=True, reason=""):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.source = source
        self.available = bool(available)
        self.reason = reason

    def vector(self):
        return (self.x, self.y, self.z)

    def as_dict(self):
        return {
            "x": self.x, "y": self.y, "z": self.z,
            "magnitude": gravity_magnitude((self.x, self.y, self.z)),
            "source": self.source,
            "available": self.available,
            "reason": self.reason,
        }


class IIOAccelSource:
    """Read the first matching IIO accelerometer device under a root."""

    def __init__(self, root="/", name_hints=None, channels=None,
                 scale_files=None, matrix=None):
        self.root = root.rstrip("/") or "/"
        self.name_hints = name_hints or ("accel",)
        self.channels = channels or (
            "in_accel_x_raw", "in_accel_y_raw", "in_accel_z_raw")
        self.scale_files = scale_files or ("in_accel_scale", "in_accel_x_scale")
        self.matrix = matrix

    def _device(self):
        for dev in sorted(glob.glob(self.root + "/sys/bus/iio/devices/iio:device*")):
            try:
                with open(os.path.join(dev, "name")) as f:
                    name = f.read().strip()
            except OSError:
                continue
            if any(hint and hint.lower() in name.lower() for hint in self.name_hints):
                return dev
        return None

    def _scale(self, dev):
        for fn in self.scale_files:
            try:
                with open(os.path.join(dev, fn)) as f:
                    val = float(f.read().strip())
                if val > 0:
                    return val
            except (OSError, ValueError):
                continue
        return None

    def read(self):
        dev = self._device()
        if dev is None:
            raise SourceUnavailable("no matching IIO accelerometer device")
        raw = []
        for ch in self.channels:
            path = os.path.join(dev, ch)
            try:
                with open(path) as f:
                    raw.append(int(f.read().strip()))
            except (OSError, ValueError):
                raise SourceUnavailable("IIO channel unreadable: %s" % ch)
        scale = self._scale(dev)
        # When no scale is exposed we cannot convert to m/s^2 honestly.
        if scale is None:
            raise SourceUnavailable("IIO accelerometer has no readable scale")
        x, y, z = (v * scale for v in raw)
        x, y, z = apply_mount_matrix((x, y, z), self.matrix)
        return SensorReading(x, y, z, source="iio-accel:" + os.path.basename(dev))


class SensorProxySource:
    """Decode iio-sensor-proxy's D-Bus ``AccelerometerOrientation``.

    The proxy reports a coarse orientation string rather than a gravity vector,
    so this source maps it to the matching discrete pose and a synthetic
    reference gravity vector. It is ONLY used when iio-sensor-proxy actually
    claims an accelerometer (``HasAccelerometer``).
    """

    # net.hadess.SensorProxy AccelerometerOrientation -> pose (degrees).
    ORIENT_MAP = {
        "normal": 0,
        "bottom-up": 180,
        "left-up": 90,
        "right-up": 270,
        "undefined": None,
    }

    def __init__(self, reference=None, bus=None):
        self.reference = reference
        self._bus = bus

    def _bus_obj(self):
        if self._bus is not None:
            return self._bus
        import dbus  # only imported when this source is actually used
        return dbus.SystemBus()

    def read(self):
        try:
            bus = self._bus_obj()
            obj = bus.get_object("net.hadess.SensorProxy",
                                 "/net/hadess/SensorProxy")
            props = __import__("dbus").Interface(
                obj, "org.freedesktop.DBus.Properties")
            has = bool(props.Get("net.hadess.SensorProxy", "HasAccelerometer"))
            orient = str(props.Get("net.hadess.SensorProxy",
                                   "AccelerometerOrientation"))
        except Exception as exc:  # dbus absent, service absent, claim refused
            raise SourceUnavailable("iio-sensor-proxy unavailable: %s" % exc)
        if not has:
            raise SourceUnavailable("iio-sensor-proxy reports no accelerometer")
        deg = self.ORIENT_MAP.get(orient)
        if deg is None:
            raise SourceUnavailable("iio-sensor-proxy orientation is undefined")
        refs = {
            0: (0.0, -1.0, 0.0), 90: (1.0, 0.0, 0.0),
            180: (0.0, 1.0, 0.0), 270: (-1.0, 0.0, 0.0),
        }
        if isinstance(self.reference, dict):
            for k in ("0", "90", "180", "270"):
                v = self.reference.get(k)
                if isinstance(v, (list, tuple)) and len(v) == 3:
                    refs[int(k)] = tuple(float(x) for x in v)
        gx, gy, gz = refs[deg]
        return SensorReading(gx * G_MS2, gy * G_MS2, gz * G_MS2,
                             source="iio-sensor-proxy")


class ManualSource:
    """Explicit owner-supplied vector (diagnostics/tests only)."""

    def __init__(self, x=0.0, y=-G_MS2, z=0.0):
        self.x, self.y, self.z = x, y, z

    def read(self):
        return SensorReading(self.x, self.y, self.z, source="manual")


def resolve_source(name, config=None):
    """Build a sensor source by name using the orientation document's config."""
    cfg = config or {}
    sensor_cfg = cfg.get("sensor", {})
    iio_cfg = sensor_cfg.get("iio", {})
    matrix = sensor_cfg.get("mount_matrix", {}).get("matrix")
    grav_ref = sensor_cfg.get("gravity_reference", {})

    if name == "iio-accel":
        return IIOAccelSource(
            name_hints=iio_cfg.get("name_hints"),
            channels=iio_cfg.get("channels"),
            scale_files=iio_cfg.get("scale_files"),
            matrix=matrix,
        )
    if name == "iio-sensor-proxy":
        return SensorProxySource(reference=grav_ref)
    if name == "manual":
        return ManualSource()
    raise SourceUnavailable("unknown sensor source: %r" % (name,))


def probe_sources(config=None):
    """Return a per-source availability report WITHOUT fabricating a reading.

    Each entry is ``{source, available, reason}``. ``available=True`` only when
    the source can actually be constructed and (for IIO) a device is present.
    """
    cfg = config or {}
    order = cfg.get("sensor", {}).get("sources", ["iio-accel", "iio-sensor-proxy", "manual"])
    out = []
    for name in order:
        # auto_capable: can drive real auto-rotation (a live gravity source).
        # `manual` is a diagnostic source only, never auto_capable.
        entry = {"source": name, "available": False, "auto_capable": False, "reason": ""}
        try:
            src = resolve_source(name, cfg)
        except SourceUnavailable as exc:
            entry["reason"] = str(exc)
            out.append(entry)
            continue
        if name == "iio-accel":
            if src._device() is None:
                entry["reason"] = "no IIO accelerometer device present"
            elif src._scale(src._device()) is None:
                entry["reason"] = "IIO device present but no readable scale"
            else:
                entry["available"] = True
                entry["auto_capable"] = True
        elif name == "manual":
            entry["available"] = True
            entry["auto_capable"] = False
        elif name == "iio-sensor-proxy":
            try:
                src.read()
                entry["available"] = True
                entry["auto_capable"] = True
            except SourceUnavailable as exc:
                entry["reason"] = str(exc)
        out.append(entry)
    return out
