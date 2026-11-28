"""PWNAGE-54000: real sensor-hub start/control (no synthetic readings)."""

import os

from nuxel_orientation.sensors import (
    SensorHubControl, gravity_magnitude, parse_raw_gravity,
)


def make_root(tmp_path, *, lhd=True, linker=True, raw="0,0,0\n",
              enable="0\n", power="1\n"):
    root = tmp_path
    paths = {
        "raw": "/sys/class/sensors/accelerometer_sensor/raw_data",
        "enable": "/sys/class/sensors/ssp_sensor/enable",
        "power": "/sys/class/sec/sensorhub/mcu_power",
        "bbd": "/dev/bbd_control",
        "lhd": "/vendor/bin/hw/lhd",
        "linker": "/system/bin/linker64",
    }
    for key, rel in paths.items():
        full = root / rel.lstrip("/")
        full.parent.mkdir(parents=True, exist_ok=True)
        if key in ("raw",):
            full.write_text(raw)
        elif key == "enable":
            full.write_text(enable)
        elif key == "power":
            full.write_text(power)
        elif key == "bbd":
            full.write_text("")
        elif key == "lhd" and lhd:
            full.write_text("lhd")
        elif key == "linker" and linker:
            full.write_text("linker")
    if not lhd:
        (root / "vendor/bin/hw/lhd").unlink(missing_ok=True)
    if not linker:
        (root / "system/bin/linker64").unlink(missing_ok=True)
    return paths


def control(root, paths, **kw):
    kw.setdefault("startup_timeout_ms", 100)
    return SensorHubControl(
        root=str(root),
        raw_path=paths["raw"], enable_path=paths["enable"],
        power_path=paths["power"], bbd_control_path=paths["bbd"],
        lhd_paths=[paths["lhd"]], linker_paths=[paths["linker"]],
        **kw,
    )


def test_parse_raw_gravity_accepts_comma_and_semicolon():
    assert parse_raw_gravity("1,2,3") == (1.0, 2.0, 3.0)
    assert parse_raw_gravity("1;2;3") == (1.0, 2.0, 3.0)
    assert parse_raw_gravity("garbage") is None
    assert parse_raw_gravity(None) is None


def test_missing_lhd_is_reported_and_no_doomed_write(tmp_path):
    paths = make_root(tmp_path, lhd=False)
    hub = control(tmp_path, paths, retry_interval_ms=0)
    status = hub.ensure_streaming()
    assert status["streaming"] is False
    assert status["lhd_present"] is False
    assert "lhd" in status["reason"].lower()
    # We must not pretend a write can patch a missing MCU runtime.
    assert (tmp_path / paths["enable"].lstrip("/")).read_text().strip() == "0"
    assert (tmp_path / paths["bbd"].lstrip("/")).read_text() == ""


def test_present_lhd_never_synthesises_esw_ready(tmp_path):
    """Premature ESW:READY publication is removed (SSP protocol contract).

    With no native bridge ABI the daemon is a consumer only; it must not write
    ESW:READY into /dev/bbd_control or touch the enable bits, even when the
    vendor lhd runtime appears present.  It reports the hub unavailable and
    leaves the control nodes untouched.
    """
    paths = make_root(tmp_path, lhd=True, linker=True, raw="0,0,0\n")
    hub = control(tmp_path, paths, retry_interval_ms=0, auto_start=True)
    status = hub.ensure_streaming()
    assert status["lhd_present"] is True
    assert status["android_linker_present"] is True
    assert status["streaming"] is False
    # No ESW:READY, no enable-bit write, ever.
    assert (tmp_path / paths["bbd"].lstrip("/")).read_text() == ""
    assert (tmp_path / paths["enable"].lstrip("/")).read_text().strip() == "0"


def test_existing_enable_bits_are_not_modified(tmp_path):
    """The daemon is a consumer: it must not OR extra enable bits."""
    paths = make_root(tmp_path, enable="6\n")  # gyro/other bits already set
    hub = control(tmp_path, paths, retry_interval_ms=0)
    status = hub.ensure_streaming()
    # enable buffer is left exactly as-is (6), never bumped to 7.
    assert status["enable_bits"] == 6
    assert (tmp_path / paths["enable"].lstrip("/")).read_text().strip() == "6"


def test_live_raw_data_needs_no_write_and_is_auto_capable(tmp_path):
    paths = make_root(tmp_path, raw="0,-1000,0\n", enable="0\n")
    hub = control(tmp_path, paths, retry_interval_ms=0)
    status = hub.ensure_streaming()
    assert status["streaming"] is True
    assert status["raw_data"] == "0,-1000,0"
    assert gravity_magnitude(parse_raw_gravity(status["raw_data"])) > 0
    # A live stream means no control write was needed.
    assert (tmp_path / paths["enable"].lstrip("/")).read_text().strip() == "0"


def test_auto_start_disabled_never_writes(tmp_path):
    paths = make_root(tmp_path)
    hub = control(tmp_path, paths, auto_start=False, retry_interval_ms=0)
    status = hub.ensure_streaming()
    assert status["streaming"] is False
    assert (tmp_path / paths["enable"].lstrip("/")).read_text().strip() == "0"
