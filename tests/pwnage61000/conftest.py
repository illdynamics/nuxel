import importlib.machinery
import importlib.util
import os
import pathlib
import struct

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_script(name, relpath):
    path = ROOT / relpath
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec and spec.loader, path
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def diag():
    return load_script("nuxel_mfc_diag_p61000", "tools/s10plus/a61/nuxel-mfc-diag")


@pytest.fixture
def play():
    return load_script("nuxel_mfc_play_p61000", "tools/s10plus/a61/nuxel-mfc-play")


def make_video_node(root, video, name, platform, driver, compatible, ip_ver):
    """Build a fake sysfs video4linux node (never a real /dev node)."""
    node = root / "class" / "video4linux" / video
    node.mkdir(parents=True, exist_ok=True)
    (node / "name").write_text(name + "\n")
    (node / "index").write_text("0\n")
    (node / "dev").write_text("81:0\n")
    devdir = root / "devices" / "platform" / platform
    devdir.mkdir(parents=True, exist_ok=True)
    drv = root / "bus" / "platform" / "drivers" / driver
    drv.mkdir(parents=True, exist_ok=True)
    (devdir / "driver").symlink_to(drv)
    if compatible is not None:
        of = devdir / "of_node"
        of.mkdir(exist_ok=True)
        (of / "compatible").write_bytes(compatible.encode() + b"\x00")
        if ip_ver is not None:
            (of / "ip_ver").write_bytes(struct.pack(">I", ip_ver))
    (node / "device").symlink_to(devdir)
