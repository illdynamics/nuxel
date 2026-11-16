"""Host tests for patch-file parsing + control constants (no hardware)."""
import sys, os, json, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import nuxel_control as ctl


def test_rpc_sensor_response_id():
    # From the GPL enum (bbd_rpc_lh.c): IRpcA..L (0..31), SensorRequest=32,
    # SensorResponse=33.
    assert ctl.RPC_SENSOR_RESPONSE == 33


def test_control_strings_present():
    for s in (ctl.ESW_CTRL_READY, ctl.BBD_CTRL_SSI_PATCH_BEGIN,
              ctl.BBD_CTRL_GPS_ON, ctl.BBD_CTRL_GPS_OFF,
              ctl.BBD_CTRL_LHD_STOP):
        assert isinstance(s, str) and s


def test_patch_blob_parse():
    # Build a synthetic patch file matching the /dev/bbd_patch C-array format.
    blob = bytes(range(256))
    header = (b"<FormatVersion=0x00010003>\n"
              b"<Crc=193>\n"
              b"<BlobLength=%d>\n"
              b"<AsicVersion=0x004775B0>\n"
              b"<Name=bcm_sensorhub_a1>\n"
              b"<Type=Application>\n"
              b"<PatchAddress=0x00800161>\n"
              b"<Blob=" % len(blob))
    hexstr = blob.hex().encode() + b">\n\x00"
    data = header + hexstr
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".patch", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        head, outblob, meta = ctl.patch_blob_from_file(path)
        assert outblob == blob
        assert meta["AsicVersion"] == "0x004775B0"
        assert meta["Name"] == "bcm_sensorhub_a1"
        assert int(meta["BlobLength"]) == len(blob)
    finally:
        os.unlink(path)


def test_real_firmware_artifact_parses():
    # The captured owner-device firmware must decode to exactly BlobLength bytes
    # and identify BCM4773 (AsicVersion=0x004775B0).
    p = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                     "docs", "hardware", "gps", "evidence", "bcm_sensorhub_a1.hex.txt")
    if not os.path.exists(p):
        import pytest
        pytest.skip("firmware evidence not present")
    head, blob, meta = ctl.patch_blob_from_file(p)
    assert meta["AsicVersion"] == "0x004775B0"
    assert meta["Name"] == "bcm_sensorhub_a1"
    assert len(blob) == int(meta["BlobLength"]) == 438895
    assert hashlib.sha256(blob).hexdigest() == "56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d"


def test_fw_json_consistent():
    p = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                     "docs", "hardware", "gps", "evidence", "verified-firmware.json")
    if not os.path.exists(p):
        import pytest
        pytest.skip("firmware evidence not present")
    d = json.load(open(p))
    assert d["chip"] == "BCM4773 (AsicVersion=0x004775B0)"
    assert d["blob_length"] == 438895
    assert d["loaded_into_chip"] is False


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
