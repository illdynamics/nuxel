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
import time

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


# ---------------------------------------------------------------------------
# Sensor-hub control (S10+ BCM47752 + LSM6DSO)
# ---------------------------------------------------------------------------
#
# The accelerometer behind the Broadcom SSP hub is not a normal IIO device:
# ``/sys/class/sensors/accelerometer_sensor/raw_data`` stays ``0,0,0`` until
# userspace (a) brings the MCU out of shutdown and (b) sets the accelerometer
# enable bit in ``/sys/class/sensors/ssp_sensor/enable``.  Android's vendor
# ``lhd`` daemon normally performs the BBD/LHD patch handshake.  Nuxel cannot
# fabricate that handshake, but it *must* drive the two kernel interfaces that
# do exist so a working LHD runtime, when present, starts streaming without a
# manual shell command.  Every operation below is a real kernel interface; no
# synthetic reading is ever produced.

HUB_RAW_DATA = "/sys/class/sensors/accelerometer_sensor/raw_data"
HUB_ENABLE = "/sys/class/sensors/ssp_sensor/enable"
HUB_MCU_POWER = "/sys/class/sec/sensorhub/mcu_power"
HUB_BBD_CONTROL = "/dev/bbd_control"
HUB_LHD_PATHS = ("/vendor/bin/hw/lhd", "/vendor/bin/lhd")
HUB_LINKER_PATHS = ("/system/bin/linker64",)

def _read_text_file(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except OSError:
        return ""


def parse_raw_gravity(raw):
    """Parse ``x,y,z`` or ``x;y;z`` into a tuple, or return ``None``."""
    try:
        parts = [p.strip() for p in str(raw).replace(";", ",").split(",")]
        if len(parts) < 3:
            return None
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except (TypeError, ValueError):
        return None


class SensorHubControl:
    """Drive the S10+ sensor-hub kernel control nodes honestly.

    ``ensure_streaming`` performs the two operations Nuxel can legitimately
    perform from Fedora userspace:

    * write ``ESW:READY`` to ``/dev/bbd_control`` so the kernel's BBD/SSP
      bridge initialises the MCU when an LHD patch runtime is available;
    * set the accelerometer bit in ``/sys/class/sensors/ssp_sensor/enable``.

    It then *waits for a real non-zero ``raw_data`` sample*.  If the Android
    ``lhd`` runtime (or its bionic linker) is absent, the MCU cannot be
    patched and this method returns ``streaming=False`` with that exact reason.
    """

    def __init__(self, root="/", raw_path=None, enable_path=None,
                 power_path=None, bbd_control_path=None, lhd_paths=None,
                 linker_paths=None, startup_timeout_ms=1500,
                 retry_interval_ms=30000, enable_bit=1, auto_start=True):
        self.root = (root or "/").rstrip("/")
        self.raw_path = raw_path or HUB_RAW_DATA
        self.enable_path = enable_path or HUB_ENABLE
        self.power_path = power_path or HUB_MCU_POWER
        self.bbd_control_path = bbd_control_path or HUB_BBD_CONTROL
        self.lhd_paths = tuple(lhd_paths or HUB_LHD_PATHS)
        self.linker_paths = tuple(linker_paths or HUB_LINKER_PATHS)
        self.startup_timeout_ms = max(0, int(startup_timeout_ms))
        self.retry_interval_ms = max(0, int(retry_interval_ms))
        self.enable_bit = int(enable_bit)
        self.auto_start = bool(auto_start)
        self._last_attempt = 0.0
        self._last_status = None

    def _p(self, path):
        if not path:
            return path
        if self.root and self.root != "/":
            return os.path.join(self.root, path.lstrip("/"))
        return path

    def _present(self, paths):
        for path in paths:
            if os.path.exists(self._p(path)):
                return self._p(path)
        return None

    def status(self):
        raw = _read_text_file(self._p(self.raw_path))
        gravity = parse_raw_gravity(raw)
        magnitude = gravity_magnitude(gravity) if gravity else 0.0
        raw_live = bool(gravity and magnitude >= 1.0)
        enable_raw = _read_text_file(self._p(self.enable_path))
        try:
            enable_bits = int(enable_raw, 10)
        except (TypeError, ValueError):
            enable_bits = None
        power_raw = _read_text_file(self._p(self.power_path))
        lhd = self._present(self.lhd_paths)
        linker = self._present(self.linker_paths)
        reason = ""
        if not raw_live:
            if not lhd:
                reason = ("vendor Android lhd daemon is not installed; the "
                          "BCM47752 MCU cannot receive its BBD/LHD patch")
            elif not linker:
                reason = ("vendor lhd is present but /system/bin/linker64 is "
                          "missing; the Android/Bionic runtime is incomplete")
            elif enable_bits is not None and not (enable_bits & self.enable_bit):
                reason = "accelerometer enable bit is clear on the sensor hub"
            else:
                reason = ("sensor-hub MCU is not streaming (kernel SSP chip-ID "
                          "or BBD transport did not come up)")
        return {
            "raw_data": raw or "unavailable",
            "raw_live": raw_live,
            "gravity": list(gravity) if gravity else None,
            "magnitude": magnitude,
            "accelerometer_enabled": bool(
                enable_bits is not None and (enable_bits & self.enable_bit)),
            "enable_bits": enable_bits,
            "mcu_powered": power_raw == "1",
            "lhd_present": bool(lhd),
            "lhd_path": lhd,
            "android_linker_present": bool(linker),
            "streaming": raw_live,
            "reason": reason,
        }

    def ensure_streaming(self, force=False):
        """Ask the kernel to start the sensor hub; verify with real raw_data."""
        now = time.monotonic()
        if not force and self._last_status and self._last_status.get("streaming"):
            return self._last_status
        if not force and self._last_attempt and (
                (now - self._last_attempt) * 1000.0 < self.retry_interval_ms):
            return self._last_status or self.status()
        self._last_attempt = now
        before = self.status()
        if before.get("streaming"):
            self._last_status = before
            return before
        if not self.auto_start:
            before["reason"] = before.get("reason") or "sensor auto-start disabled"
            self._last_status = before
            return before
        # Without the vendor LHD runtime no kernel write can patch the MCU.
        # Do not spam the kernel with doomed enable/reset transactions.
        if not before.get("lhd_present"):
            self._last_status = before
            return before
        if not before.get("android_linker_present"):
            self._last_status = before
            return before
        # 1. Bring the MCU out of shutdown / request a fresh BBD handshake.
        if os.path.exists(self._p(self.bbd_control_path)):
            try:
                with open(self._p(self.bbd_control_path), "w") as f:
                    f.write("ESW:READY")
            except OSError:
                pass
        # 2. Preserve any existing sensor bits and set accelerometer (bit 0).
        try:
            current = int(_read_text_file(self._p(self.enable_path)) or "0", 10)
        except ValueError:
            current = 0
        wanted = current | self.enable_bit
        if wanted != current:
            try:
                with open(self._p(self.enable_path), "w") as f:
                    f.write("%d" % wanted)
            except OSError:
                pass
        # 3. Verify with a real sample; never synthesize one.
        deadline = time.monotonic() + self.startup_timeout_ms / 1000.0
        status = self.status()
        while not status.get("streaming") and time.monotonic() < deadline:
            time.sleep(0.05)
            status = self.status()
        if not status.get("streaming"):
            status["reason"] = (
                "sensor-hub MCU did not stream after enable (LHD patch "
                "handshake/chip-ID failed)")
        self._last_status = status
        return status


def hub_control_from_config(config=None, root="/"):
    cfg = ((config or {}).get("sensor", {}) or {}).get("sensor_hub", {}) or {}
    return SensorHubControl(
        root=cfg.get("root", root),
        raw_path=cfg.get("raw_data"),
        enable_path=cfg.get("enable"),
        power_path=cfg.get("mcu_power"),
        bbd_control_path=cfg.get("bbd_control"),
        lhd_paths=cfg.get("lhd_paths"),
        linker_paths=cfg.get("linker_paths"),
        startup_timeout_ms=cfg.get("startup_timeout_ms", 1500),
        retry_interval_ms=cfg.get("retry_interval_ms", 30000),
        enable_bit=cfg.get("enable_bit", 1),
        auto_start=cfg.get("auto_start", True),
    )


def ensure_sensor_hub(config=None, force=False, root="/"):
    """Production entry point used by the daemon before an Auto probe."""
    return hub_control_from_config(config, root=root).ensure_streaming(force=force)


class SysfsAccelSource:
    """Read the Samsung sensor-hub accelerometer factory node.

    The S10+ sensor hub (BCM47752 + LSM6DSO) exposes a real, live gravity
    vector at ``/sys/class/sensors/accelerometer_sensor/raw_data`` when the hub
    MCU is running and the accelerometer is enabled.  The node is NOT a fake
    diagnostic source: a zero vector means the hub is down/unstarted and this
    class reports that honestly.

    Raw units are LSM6DSO LSBs (not m/s^2).  The orientation policy only needs
    direction plus a physically plausible magnitude, so a non-zero sample is
    normalised to one standard gravity.  This keeps the policy thresholds
    meaningful without pretending to know the factory calibration scale.
    """

    PATH = "/sys/class/sensors/accelerometer_sensor/raw_data"

    def __init__(self, path=None, matrix=None):
        self.path = path or self.PATH
        self.matrix = matrix

    def read(self):
        try:
            with open(self.path) as f:
                raw = f.read().strip()
        except OSError as exc:
            raise SourceUnavailable("sensor-hub raw_data unreadable: %s" % exc)
        parts = [p.strip() for p in raw.replace(";", ",").split(",")]
        if len(parts) < 3:
            raise SourceUnavailable("sensor-hub raw_data is malformed: %r" % raw)
        try:
            x, y, z = (float(parts[0]), float(parts[1]), float(parts[2]))
        except ValueError:
            raise SourceUnavailable("sensor-hub raw_data is not numeric: %r" % raw)
        mag = gravity_magnitude((x, y, z))
        if mag < 1.0:
            raise SourceUnavailable("sensor-hub accelerometer is zero (MCU not streaming)")
        # Normalise the LSB vector to 1 g so the policy's weak/flat thresholds
        # are meaningful.  Direction (the part rotation uses) is unchanged.
        scale = G_MS2 / mag
        x, y, z = x * scale, y * scale, z * scale
        x, y, z = apply_mount_matrix((x, y, z), self.matrix)
        return SensorReading(x, y, z, source="iio-sysfs-accel")


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
    if name in ("iio-sysfs-accel", "sensor-hub"):
        hub_cfg = sensor_cfg.get("sensor_hub", {}) or {}
        return SysfsAccelSource(path=hub_cfg.get("raw_data"), matrix=matrix)
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
                # A node/scale alone is not a live sensor.  Read one sample and
                # require a physically plausible, non-zero gravity magnitude.
                # Zero/stale samples must never enable auto rotation.
                try:
                    reading = src.read()
                    mag = gravity_magnitude(reading.vector())
                    if reading.available and mag >= 2.0:
                        entry["available"] = True
                        entry["auto_capable"] = True
                        entry["sample"] = reading.as_dict()
                    else:
                        entry["reason"] = (
                            "IIO accelerometer sample is zero/implausible "
                            "(|g|=%.3f m/s^2)" % mag)
                except SourceUnavailable as exc:
                    entry["reason"] = str(exc)
                except Exception as exc:
                    entry["reason"] = "IIO accelerometer read failed: %s" % exc
        elif name in ("iio-sysfs-accel", "sensor-hub"):
            try:
                hub = hub_control_from_config(cfg).status()
                entry["hub"] = hub
                reading = src.read()
                mag = gravity_magnitude(reading.vector())
                # Normalised samples are 1 g by construction; accept a generous
                # band so a real hub sample is never mistaken for a test value.
                if 7.0 <= mag <= 12.0:
                    entry["available"] = True
                    entry["auto_capable"] = True
                    entry["sample"] = reading.as_dict()
                    entry["source"] = "iio-sysfs-accel"
                else:
                    entry["reason"] = hub.get("reason") or (
                        "sensor-hub sample implausible (|g|=%.3f)" % mag)
            except SourceUnavailable as exc:
                entry["reason"] = str(exc)
            except Exception as exc:
                entry["reason"] = "sensor-hub read failed: %s" % exc
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
