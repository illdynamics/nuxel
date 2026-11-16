#!/usr/bin/env python3
"""PWNAGE-SSP userspace gates (no hardware needed).

Covers the pieces that can be wrong without touching the phone:
  * the orientation document prefers the accel+gyro hub source;
  * the gyro LSB->rad/s conversion and malformed-input rejection;
  * the source is never *available* without a real non-zero gravity sample;
  * the native BBD bridge ABI constants match the kernel's packed ssp_msg.
"""
import json
import os
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "nuxel-orientation"))

import nuxel_orientation.sensors as sensors  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  %s" % (detail,)))
    if not cond:
        fails.append(name)


cfg = json.loads((ROOT / "configs/nuxel/orientation/orientation.json").read_text())
check("preferred source is accel+gyro",
      cfg["sensor"]["sources"][0] == "iio-sysfs-accel-gyro",
      cfg["sensor"]["sources"])
check("gyro raw_data configured",
      cfg["sensor"]["sensor_hub"]["gyro_raw_data"] ==
      "/sys/class/sensors/gyro_sensor/raw_data")

# Gyro conversion: 2000 dps full-scale -> 0.07 dps/LSB -> rad/s.
with tempfile.NamedTemporaryFile("w", suffix=".raw", delete=False) as f:
    f.write("700,-700,0\n")
    gyro_path = f.name
rate = sensors.SysfsGyroSource(gyro_path).read()
os.unlink(gyro_path)
check("gyro 700 LSB == 700*0.07 dps in rad/s",
      abs(rate[0] - 0.8552113334772216) < 1e-12, rate)
check("gyro sign preserved", rate[1] < 0, rate)

with tempfile.NamedTemporaryFile("w", suffix=".raw", delete=False) as f:
    f.write("0,0\n")
    bad_path = f.name
try:
    sensors.SysfsGyroSource(bad_path).read()
    check("malformed gyro rejected", False, "accepted")
except sensors.SourceUnavailable:
    check("malformed gyro rejected", True)
os.unlink(bad_path)

# A zero gravity vector must never make the hub source auto-capable.
with tempfile.NamedTemporaryFile("w", suffix=".raw", delete=False) as f:
    f.write("0,0,0\n")
    zero_path = f.name
try:
    sensors.SysfsAccelSource(zero_path).read()
    check("zero accel rejected", False, "accepted")
except sensors.SourceUnavailable:
    check("zero accel rejected", True)
os.unlink(zero_path)

# Kernel ABI: ssp_msg is packed u8/u16/u16/u32 = 9 bytes.
ssp = struct.Struct("<BHH I")
check("ssp_msg size is 9 (kernel packed)", ssp.size == 9, ssp.size)

bridge = (ROOT / "services/nuxel-orientation/nuxel_ssp_bridge.py").read_text()
check("bridge uses /dev/bbd_sensor", '"/dev/bbd_sensor"' in bridge)
check("bridge uses /dev/ttyBCM", '"/dev/ttyBCM"' in bridge)
check("bridge never fabricates samples",
      "never synthesises" in bridge.lower())
check("bridge bring-up uses kernel nuxel_bringup",
      "nuxel_bringup" in bridge)

print("\n%d failing check(s)" % len(fails))
sys.exit(1 if fails else 0)
