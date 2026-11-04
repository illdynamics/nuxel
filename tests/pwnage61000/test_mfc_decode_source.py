import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "tools/s10plus/a61/nuxel-mfc-decode.c"


def test_vendor_abi_choices():
    text = SRC.read_text()
    code = text.split("*/", 1)[1]  # skip the explanatory header comment
    assert "V4L2_MEMORY_DMABUF" in code         # capture side
    assert "V4L2_MEMORY_USERPTR" in code        # output side
    assert "VIDIOC_DECODER_CMD" not in code      # this vendor driver has no stateful command API
    assert "V4L2_EVENT_SOURCE_CHANGE" not in code
    assert "V4L2_MEMORY_MMAP" not in code        # MMAP is explicitly rejected by the driver
    assert "request_firmware" not in code


def test_helper_has_explicit_safety_gate():
    text = SRC.read_text()
    assert "--allow-hardware-open" in text
    assert "safety receipt" in text.lower()
    assert "EXPECTED_DRIVER" in text
    assert "DECODER_SYSFS_NAME" in text
    assert "udmabuf" in text


def test_helper_builds_natively_and_refuses_without_flag(tmp_path):
    cc = shutil.which("cc")
    if not cc:
        pytest.skip("no host cc")
    out = tmp_path / "nuxel-mfc-decode"
    p = subprocess.run([cc, "-O2", "-Wall", "-Wextra", "-Wno-unused-parameter",
                        "-Wno-format-truncation", "-o", str(out), str(SRC)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    r = subprocess.run([str(out), "--version"], capture_output=True, text=True)
    assert r.returncode == 0 and "nuxel-mfc-decode" in r.stdout
    r = subprocess.run([str(out), "--query-only", "--device", "/dev/video6"],
                       capture_output=True, text=True)
    assert r.returncode == 2
    assert "REFUSED" in (r.stdout + r.stderr)


def test_cross_compiled_aarch64_binary_if_present():
    p = ROOT / "build/pwnage61000/nuxel-mfc-decode"
    if not p.is_file():
        pytest.skip("cross-compiled artifact not built")
    assert subprocess.run(["file", str(p)], capture_output=True, text=True).stdout.find("ARM aarch64") >= 0
