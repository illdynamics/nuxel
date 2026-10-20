#!/usr/bin/env python3
"""Positive and negative tests for the fresh-image parity verifier.

The fixture is deliberately tiny: it exercises the same source/target mapping,
AArch64 ELF gate, symlink resolution, in-image manifest and host-architecture
scan as the real S10+ inventory, without a four-gigabyte image.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PARITY = HERE.parent
ROOT = PARITY.parents[2]
VERIFY = PARITY / "verify-image-parity.py"
GENERATE = PARITY / "generate-userspace-manifest.py"


def elf(machine: int = 183) -> bytes:
    h = bytearray(64)
    h[:4] = b"\x7fELF"
    h[4] = 2       # ELFCLASS64
    h[5] = 1       # ELFDATA2LSB
    h[6] = 1       # EV_CURRENT
    struct.pack_into("<H", h, 16, 2)    # ET_EXEC
    struct.pack_into("<H", h, 18, machine)
    struct.pack_into("<I", h, 20, 1)    # e_version
    struct.pack_into("<Q", h, 32, 0)    # e_phoff
    struct.pack_into("<Q", h, 40, 0)    # e_shoff
    struct.pack_into("<H", h, 52, 64)   # e_ehsize
    struct.pack_into("<H", h, 54, 56)   # e_phentsize
    struct.pack_into("<H", h, 56, 0)    # e_phnum
    struct.pack_into("<H", h, 58, 64)   # e_shentsize
    struct.pack_into("<H", h, 60, 0)    # e_shnum
    return bytes(h)


def make_fixture(base: Path) -> tuple[Path, Path]:
    repo = base / "repo"
    stage = base / "stage"
    (repo / "src/tree").mkdir(parents=True)
    (repo / "src/tree/index.html").write_text("<!doctype html><title>fixture</title>\n")
    (repo / "src/tree/js").mkdir()
    (repo / "src/tree/js/app.js").write_text("console.log('fixture');\n")
    (repo / "units").mkdir()
    (repo / "units/tool.service").write_text("[Unit]\nDescription=fixture\n[Service]\nExecStart=/usr/lib/nuxel/tool\n[Install]\nWantedBy=multi-user.target\n")
    (repo / "src").mkdir(exist_ok=True)
    (repo / "src/tool.c").write_text("int main(void){return 0;}\n")
    (repo / "VERSION").write_text("v-test\n")
    (repo / "images/s10plus").mkdir(parents=True)
    (repo / "images/s10plus/build-phone-rootfs-inside-fedora.sh").write_text(
        "cp -a /nuxel/src/tree /stage\n"
        "install /nuxel/units/tool.service /stage\n"
        "gcc /nuxel/src/tool.c\n")
    inventory = {
        "schema": "nuxel.image-payload-parity/1",
        "release": "v-test",
        "source_trees": [{"id": "tree", "source": "src/tree", "target": "/usr/share/nuxel/tree", "required": True}],
        "source_files": [{"id": "unit", "source": "units/tool.service", "target": "/etc/systemd/system/tool.service", "mode": "0644"}],
        "built_elf": [{"id": "tool", "source": "src/tool.c", "target": "/usr/lib/nuxel/tool", "mode": "0755"}],
        "symlinks": [{"id": "tree-link", "path": "/usr/share/nuxel/tree-link", "points_to": "tree", "required": True}],
        "enablement": [{"id": "tool-enable", "path": "/etc/systemd/system/multi-user.target.wants/tool.service", "points_to": "../tool.service", "required": True}],
        "webroot": ["/usr/share/nuxel/tree/index.html"],
        "required_packages": [],
        "normalization": {},
    }
    (repo / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    # Stage the payload.
    shutil.copytree(repo / "src/tree", stage / "usr/share/nuxel/tree")
    (stage / "usr/share/nuxel/tree-link").symlink_to("tree")
    (stage / "etc/systemd/system/multi-user.target.wants").mkdir(parents=True)
    shutil.copy2(repo / "units/tool.service", stage / "etc/systemd/system/tool.service")
    (stage / "etc/systemd/system/multi-user.target.wants/tool.service").symlink_to("../tool.service")
    (stage / "usr/lib/nuxel").mkdir(parents=True)
    (stage / "usr/lib/nuxel/tool").write_bytes(elf())
    (stage / "usr/lib/nuxel/tool").chmod(0o755)
    return repo, stage


def run(repo: Path, stage: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VERIFY), "--staging", str(stage), "--repo", str(repo),
         "--inventory", str(repo / "inventory.json")],
        text=True, capture_output=True, timeout=60)


def generate(repo: Path, stage: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GENERATE), "--root", str(stage), "--repo", str(repo),
         "--inventory", str(repo / "inventory.json"),
         "--output", "/etc/nuxel/userspace-manifest.json",
         "--version", "v-test", "--source-date-epoch", "0", "--no-rpm"],
        text=True, capture_output=True, timeout=60)


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory(prefix="nuxel-parity-test-") as tmp:
        base = Path(tmp)
        repo, stage = make_fixture(base)
        gen = generate(repo, stage)
        if gen.returncode != 0:
            print(gen.stdout, gen.stderr)
            failures.append("manifest generation failed")
        pos = run(repo, stage)
        print(pos.stdout.strip())
        if pos.returncode != 0:
            failures.append("positive fixture did not pass")

        # 1. Missing daemon/binary.
        tool = stage / "usr/lib/nuxel/tool"
        saved = tool.read_bytes()
        tool.unlink()
        neg = run(repo, stage)
        if neg.returncode == 0 or "missing built ELF" not in neg.stdout:
            failures.append("missing binary was not rejected")
        tool.write_bytes(saved)
        tool.chmod(0o755)

        # 2. Host x86-64 binary.
        tool.write_bytes(elf(62))
        neg = run(repo, stage)
        if neg.returncode == 0 or "wrong ELF machine" not in neg.stdout:
            failures.append("x86-64 binary was not rejected")
        tool.write_bytes(saved)

        # 3. Mach-O binary.
        tool.write_bytes(b"\xcf\xfa\xed\xfe" + b"M" * 60)
        neg = run(repo, stage)
        if neg.returncode == 0 or "Mach-O" not in neg.stdout:
            failures.append("Mach-O binary was not rejected")
        tool.write_bytes(saved)

        # 4. Tampered payload after manifest generation.
        (stage / "usr/share/nuxel/tree/index.html").write_text("tampered\n")
        neg = run(repo, stage)
        if neg.returncode == 0 or "source/image drift" not in neg.stdout:
            failures.append("source-tree tamper was not rejected")
        (stage / "usr/share/nuxel/tree/index.html").write_text("<!doctype html><title>fixture</title>\n")

        # 5. Broken enablement link.
        link = stage / "etc/systemd/system/multi-user.target.wants/tool.service"
        link.unlink()
        link.symlink_to("../missing.service")
        neg = run(repo, stage)
        if neg.returncode == 0 or "enablement" not in neg.stdout:
            failures.append("broken enablement link was not rejected")
        link.unlink()
        link.symlink_to("../tool.service")

        # Restore a clean manifest and prove the fixture is green again.
        generate(repo, stage)
        pos = run(repo, stage)
        if pos.returncode != 0:
            failures.append("fixture did not recover after negative tests")

    if failures:
        for failure in failures:
            print("FAIL", failure)
        print("PARITY-TESTS: FAIL")
        return 1
    print("PARITY-TESTS: ALL PASS (positive + 5 negative paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
