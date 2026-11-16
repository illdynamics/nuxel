"""BBD control-string / power / patch constants for SM-G975F (beyond2lte).

Every string and value here is taken verbatim from the GPL kernel sources:

  drivers/sensorhub/brcm/bbdpl/bbd.h      (control strings)
  drivers/sensorhub/brcm/bbdpl/bbd.c      (control handling, patch read)
  drivers/sensorhub/brcm/bbdpl/bcm_gps_spi.c (power gpio, hello/bye)
"""
from __future__ import annotations

# Device nodes (bbd.c / bcm_gps_spi.c)
BBD_TRANSPORT_NODE = "/dev/ttyBCM"
BBD_PATCH_NODE = "/dev/bbd_patch"
BBD_CONTROL_NODE = "/dev/bbd_control"
BBD_SENSOR_NODE = "/dev/bbd_sensor"
BBD_URGENT_PATCH_NODE = "/dev/bbd_urgent_patch"

# GPS power rail sysfs (exported in bcm_gps_spi.c probe as GPS_PWR_EN)
GPS_POWER_RAIL = "/sys/devices/virtual/sec/gps/GPS_PWR_EN/value"

# Control strings (bbd.h)
BBD_CTRL_RESET_REQ = "BBD:RESET_REQ"
ESW_CTRL_READY = "ESW:READY"
ESW_CTRL_NOTREADY = "ESW:NOTREADY"
ESW_CTRL_CRASHED = "ESW:CRASHED"
BBD_CTRL_DEBUG_ON = "BBD:DEBUG=1"
BBD_CTRL_DEBUG_OFF = "BBD:DEBUG=0"
BBD_CTRL_PASSTHRU_ON = "BBD:PassThru=1"
BBD_CTRL_PASSTHRU_OFF = "BBD:PassThru=0"
SSP_GET_HW_REV = "SSP:GET_HW_REV"
SSP_GET_AP_REV = "SSP:GET_AP_REV"
SSP_OIS_NOTIFY_RESET = "SSP:OIS_NOTIFY_RESET"
BBD_CTRL_SSI_PATCH_BEGIN = "SSI:PassThru=1"
BBD_CTRL_SSI_PATCH_END = "SSI:PassThru=0"
GPSD_SENSOR_ON = "GPSD:SENSOR_ON"
GPSD_SENSOR_OFF = "GPSD:SENSOR_OFF"
BBD_CTRL_GPS_ON = "GPSD:CORE_ON"
BBD_CTRL_GPS_OFF = "GPSD:CORE_OFF"
BBD_CTRL_LHD_STOP = "LHD:STOP"

# RPC ids from the bbd_rpc_lh.c enum. Only the sensor-response id has a
# documented meaning in the GPL driver; the GNSS application RPCs (patch
# download, GNSS control, position solution) belong to the proprietary Samsung
# lhd/gpsd userspace and are NOT defined here.
RPC_IRpcSensorResponse_Data = 33

# Explicit mapping of the GPL enum (bbd_rpc_lh.c): RPC ids are the enum order.
# IRpc* entries are enumerated 0..31, then SensorRequest=33, SensorResponse=34.
# The sensor-response id is the only one the kernel dispatches specially.
RPC_SENSOR_RESPONSE = 33


def patch_blob_from_file(path: str) -> tuple:
    """Read the Broadcom sensor-hub patch served by /dev/bbd_patch.

    Returns (header_text_bytes, blob_bytes, metadata_dict). The file is the C
    array text form emitted by the kernel driver: ASCII "<Key=Value>" header
    lines followed by "<Blob=<hex...>>". We decode the hex blob exactly to
    <BlobLength> bytes and return the ASCII header separately so the daemon can
    feed the correct on-the-wire patch RPC to the chip.
    """
    import re
    data = open(path, "rb").read()
    header = data[:data.index(b"<Blob=")] + b"\n"
    meta = {}
    for m in re.finditer(rb"<([A-Za-z0-9]+)=([^>]*?)>", data):
        meta[m.group(1).decode()] = m.group(2).decode()
    idx = data.index(b"<Blob=") + len(b"<Blob=")
    hexstr = re.sub(rb"[^0-9A-Fa-f]", b"", data[idx:])
    blob = bytes.fromhex(hexstr.decode())
    return header, blob, meta
