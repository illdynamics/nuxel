"""Offline tests for the sensor decoding + mount matrix."""

import sys
import types

import pytest

from nuxel_orientation.sensors import (
    ManualSource, SensorProxySource, SourceUnavailable,
    apply_mount_matrix, probe_sources, resolve_source,
)


def test_apply_mount_matrix_identity():
    assert apply_mount_matrix((1, 2, 3), [1, 0, 0, 0, 1, 0, 0, 0, 1]) == (1.0, 2.0, 3.0)


def test_apply_mount_matrix_swap_xy():
    assert apply_mount_matrix((1, 2, 3), [0, 1, 0, 1, 0, 0, 0, 0, 1]) == (2.0, 1.0, 3.0)


def test_apply_mount_matrix_fallback_identity():
    assert apply_mount_matrix((1, 2, 3), None) == (1.0, 2.0, 3.0)
    assert apply_mount_matrix((1, 2, 3), [1, 0]) == (1.0, 2.0, 3.0)


def test_manual_source():
    r = ManualSource().read()
    assert r.available and r.source == "manual"
    assert r.y == pytest.approx(-9.80665)


def test_resolve_unknown_source():
    with pytest.raises(SourceUnavailable):
        resolve_source("does-not-exist")


def test_probe_sources_reports_iio_unavailable_with_impossible_hint():
    # A name hint that can never match makes IIO honestly unavailable while
    # the manual source stays available — deterministic on any host.
    config = {
        "sensor": {
            "sources": ["iio-accel", "manual"],
            "mount_matrix": {"matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1]},
            "gravity_reference": {},
            "iio": {"name_hints": ["__no_such_accel_device__"],
                    "channels": ["in_accel_x_raw", "in_accel_y_raw", "in_accel_z_raw"],
                    "scale_files": ["in_accel_scale"]},
        }
    }
    report = probe_sources(config)
    by_name = {r["source"]: r for r in report}
    assert by_name["iio-accel"]["available"] is False
    assert by_name["manual"]["available"] is True


def test_sensorproxy_orientation_map():
    sp = SensorProxySource()
    assert sp.ORIENT_MAP["normal"] == 0
    assert sp.ORIENT_MAP["bottom-up"] == 180
    assert sp.ORIENT_MAP["left-up"] == 90
    assert sp.ORIENT_MAP["right-up"] == 270
    assert sp.ORIENT_MAP["undefined"] is None


def test_sensorproxy_unavailable_without_accel():
    class FakeProps:
        def Get(self, iface, prop):
            return {"HasAccelerometer": False,
                    "AccelerometerOrientation": "normal"}[prop]

    class FakeBus:
        def get_object(self, name, path):
            return object()

    fake_dbus = types.ModuleType("dbus")
    fake_dbus.Interface = lambda obj, iface: FakeProps()
    sp = SensorProxySource(bus=FakeBus())

    had = "dbus" in sys.modules
    old = sys.modules.get("dbus")
    sys.modules["dbus"] = fake_dbus
    try:
        with pytest.raises(SourceUnavailable):
            sp.read()
    finally:
        if had:
            sys.modules["dbus"] = old
        else:
            sys.modules.pop("dbus", None)
