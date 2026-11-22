"""Stage-04 negative fixtures for real-source availability and stale-data recovery.

These are *offline* determinism tests: they prove the orientation service never
treats a missing or stale real sensor source as a live one, and that it recovers
only when a genuinely new, non-zero sample appears. No hardware is touched.
"""
import os

import pytest

from nuxel_orientation.sensors import (
    SensorHubControl, SourceUnavailable, probe_sources,
    resolve_source, SysfsAccelSource, gravity_magnitude, parse_raw_gravity,
)


# ---------------------------------------------------------------------------
# Fixtures: a synthetic sensor-hub root with a controllable raw_data node.
# ---------------------------------------------------------------------------
RAW_REL = "/sys/class/sensors/accelerometer_sensor/raw_data"
ENABLE_REL = "/sys/class/sensors/ssp_sensor/enable"
POWER_REL = "/sys/class/sec/sensorhub/mcu_power"


@pytest.fixture
def hub_root(tmp_path):
    """Return (root, raw_rel_path) with the hub control nodes laid out.

    The raw_data node starts as a *stale zero* vector, exactly like a live
    handset whose BCM47752 MCU has halted after kernel bring-up.  The returned
    second element is the RELATIVE device path (leading slash preserved) that
    the control object resolves under ``root``.
    """
    raw_path = tmp_path / RAW_REL.lstrip("/")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("0,0,0\n")
    for rel in (ENABLE_REL, POWER_REL):
        p = tmp_path / rel.lstrip("/")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("0\n" if "enable" in rel else "1\n")
    return tmp_path, RAW_REL


def _raw_file(root, raw_rel):
    return root / raw_rel.lstrip("/")


def build_control(root, raw_path, **kw):
    kw.setdefault("startup_timeout_ms", 100)
    kw.setdefault("retry_interval_ms", 0)
    return SensorHubControl(
        root=str(root),
        raw_path=raw_path,
        enable_path=ENABLE_REL,
        power_path=POWER_REL,
        bbd_control_path="/dev/bbd_control",
        lhd_paths=("/vendor/bin/hw/lhd",),
        linker_paths=("/system/bin/linker64",),
        **kw,
    )


# ---------------------------------------------------------------------------
# REAL-SOURCE-UNAVAILABLE: a real (non-manual) source that is missing or unreadable
# must be reported honestly, never silently defaulted to a fake reading.
# ---------------------------------------------------------------------------
def test_real_source_missing_file_is_unavailable(tmp_path):
    missing = tmp_path / "does_not_exist_raw"
    with pytest.raises(SourceUnavailable):
        SysfsAccelSource(path=str(missing)).read()


def test_real_source_unreadable_is_unavailable(tmp_path):
    nd = tmp_path / "raw_data"
    nd.write_text("0,0,0\n")
    os.chmod(nd, 0)  # no read permission
    try:
        with pytest.raises(SourceUnavailable):
            SysfsAccelSource(path=str(nd)).read()
    finally:
        os.chmod(nd, 0o644)


def test_real_iio_source_unavailable_reported_not_fababricated():
    # An impossible IIO name hint yields honest unavailable, never a fallback.
    config = {
        "sensor": {
            "sources": ["iio-accel"],
            "iio": {"name_hints": ["__no_such_dev__"],
                    "channels": ["in_accel_x_raw"],
                    "scale_files": ["in_accel_scale"]},
        }
    }
    report = probe_sources(config)
    assert report[0]["available"] is False
    assert report[0]["auto_capable"] is False
    assert report[0]["reason"]  # an explicit reason is recorded


def test_sensor_hub_source_unavailable_when_mcu_halted(hub_root):
    root, raw = hub_root
    # stale zero vector => unavailable, no auto-capability (read the file
    # under the synthetic root, not the host's real /sys)
    src = SysfsAccelSource(path=str(_raw_file(root, raw)))
    with pytest.raises(SourceUnavailable):
        src.read()


# ---------------------------------------------------------------------------
# STALE-DATA RECOVERY: a cached/live snapshot must not be trusted forever; a
# new non-zero sample must flip availability, and going back to zero must
# flip it off again.  Deterministic and idempotent.
# ---------------------------------------------------------------------------
def test_stale_zero_snapshot_is_not_live(hub_root):
    root, raw = hub_root
    hub = build_control(root, raw)
    status = hub.status()
    assert status["raw_live"] is False
    assert status["streaming"] is False
    assert status["magnitude"] == 0.0


def test_stale_snapshot_recovers_on_new_nonzero_sample(hub_root):
    root, raw = hub_root
    hub = build_control(root, raw)
    assert hub.status()["streaming"] is False
    # A genuine new sample appears (MCU resumed streaming).
    with open(_raw_file(root, raw), "w") as f:
        f.write("1000,-4000,2000\n")
    status = hub.status()
    assert status["streaming"] is True
    assert status["raw_live"] is True
    assert gravity_magnitude(parse_raw_gravity("1000,-4000,2000")) > 1.0


def test_stale_snapshot_goes_back_unavailable_when_stream_stops(hub_root):
    root, raw = hub_root
    hub = build_control(root, raw)
    with open(_raw_file(root, raw), "w") as f:
        f.write("1000,-4000,2000\n")
    assert hub.status()["streaming"] is True
    # Stream halts again: must NOT keep reporting live.
    with open(_raw_file(root, raw), "w") as f:
        f.write("0,0,0\n")
    assert hub.status()["streaming"] is False
    assert hub.status()["raw_live"] is False


def test_ensure_streaming_never_fabricates_on_cached_live(hub_root):
    root, raw = hub_root
    hub = build_control(root, raw)
    # Even after a brief live sample, ensure_streaming must re-verify the
    # *current* node and report the truth, not a cached "was live".
    with open(_raw_file(root, raw), "w") as f:
        f.write("0,-1000,0\n")
    assert hub.ensure_streaming()["streaming"] is True
    with open(_raw_file(root, raw), "w") as f:
        f.write("0,0,0\n")
    # force re-check (bypass the cached live shortcut)
    assert hub.ensure_streaming(force=True)["streaming"] is False


def test_probe_sources_never_auto_capable_for_stale_zero(hub_root, monkeypatch):
    root, raw = hub_root
    import nuxel_orientation.sensors as S
    monkeypatch.setattr(S, "HUB_ACCEL_RAW", raw)
    monkeypatch.setattr(S, "HUB_GYRO_RAW", raw)
    # Point the SysfsAccelSource at the stale zero node.
    config = {
        "sensor": {
            "sources": ["iio-sysfs-accel"],
            "sensor_hub": {"raw_data": raw},
        }
    }
    report = probe_sources(config)
    assert report[0]["available"] is False
    assert report[0]["auto_capable"] is False
