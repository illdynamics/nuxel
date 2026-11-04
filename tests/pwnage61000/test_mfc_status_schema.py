import json
import pathlib

import jsonschema

from conftest import make_video_node

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_schema_is_valid_and_status_validates(diag, tmp_path):
    schema = json.loads((ROOT / "tools/s10plus/a61/mfc-status.schema.json").read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    sysfs = tmp_path / "sys"
    make_video_node(sysfs, "video6", "s5p-mfc-dec0", "188d0000.mfc",
                    "s5p-mfc", "samsung,exynos-mfc", 0x1300)
    cfg = tmp_path / "config"
    cfg.write_text("CONFIG_VIDEO_EXYNOS_MFC=y\nCONFIG_VIDEOBUF2_DMA_SG=y\n"
                   "CONFIG_EXYNOS_IOMMU=y\nCONFIG_V4L2_MEM2MEM_DEV=y\n")
    fw = tmp_path / "fw"
    fw.mkdir()
    st = diag.build_status(sysfs_root=str(sysfs), dev_root=str(tmp_path / "dev"),
                           firmware_dirs=[str(fw)], config_path=str(cfg),
                           receipt_path=str(tmp_path / "none"), root=str(tmp_path))
    jsonschema.validate(st, schema)
    assert st["state"] == "BLOCKED_FIRMWARE_MISSING"


def test_state_enum_contains_required_truthful_states():
    schema = json.loads((ROOT / "tools/s10plus/a61/mfc-status.schema.json").read_text())
    states = set(schema["properties"]["state"]["enum"])
    for s in ("NOT_PRESENT", "BLOCKED_FIRMWARE_MISSING", "BLOCKED_FIRMWARE_HASH",
              "BLOCKED_DRIVER_UNSAFE", "AVAILABLE_PROBE_ONLY",
              "AVAILABLE_HARDWARE_DECODE", "AVAILABLE_SOFTWARE_ONLY"):
        assert s in states
