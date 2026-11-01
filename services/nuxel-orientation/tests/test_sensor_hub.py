"""PWNAGE-54000: the S10+ sensor-hub sysfs source is real, not a manual stub."""

import pytest

from nuxel_orientation import sensors


def test_zero_sensor_hub_sample_is_unavailable(tmp_path):
    p = tmp_path / "raw_data"
    p.write_text("0,0,0\n")
    with pytest.raises(sensors.SourceUnavailable):
        sensors.SysfsAccelSource(path=str(p)).read()


def test_sensor_hub_vector_is_normalised_to_one_g(tmp_path):
    p = tmp_path / "raw_data"
    p.write_text("1000,-4000,2000\n")
    r = sensors.SysfsAccelSource(path=str(p)).read()
    assert r.source == "iio-sysfs-accel"
    assert r.available is True
    assert 7.0 <= sensors.gravity_magnitude(r.vector()) <= 12.0


def test_sensor_hub_is_marked_auto_capable_only_when_raw_data_is_live(tmp_path, monkeypatch):
    p = tmp_path / "raw_data"
    p.write_text("120,-9,45\n")
    monkeypatch.setattr(sensors.SysfsAccelSource, "PATH", str(p))
    report = sensors.probe_sources({"sensor": {"sources": ["iio-sysfs-accel", "manual"]}})
    hub = next(s for s in report if s["source"] == "iio-sysfs-accel")
    manual = next(s for s in report if s["source"] == "manual")
    assert hub["available"] is True and hub["auto_capable"] is True
    assert manual["available"] is True and manual["auto_capable"] is False
