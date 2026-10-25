#!/usr/bin/env python3
"""Run the phone host indicator harness against the real source block.

Extracts the sensor section from both shipped phone-host sources and compiles
the same C harness against each one.  No GTK, no device.

Usage: python3 tools/s10plus/a45/test-lockscreen-indicators.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCES = [
    ROOT / "tools/s10plus/a33/nuxel-pwa-host.c",
    ROOT / "tools/s10plus/a45/nuxel-pwa-host.c",
]
HARNESS = HERE / "test-lockscreen-indicators.c"


def extract_sensor_block(text: str) -> str:
    start = text.index("/* ============================================================================\n * Lockhead indicators")
    end = text.index("/* Event-driven refresh:", start)
    return text[start:end]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nuxel-ind-c-") as work:
        workdir = Path(work)
        for source in SOURCES:
            variant = source.parent.name
            variant_dir = workdir / variant
            variant_dir.mkdir()
            snippet = extract_sensor_block(source.read_text())
            (variant_dir / "indicator_snippet.inc").write_text(snippet)
            binary = variant_dir / "test-lockscreen-indicators"
            compile_cmd = [
                os.environ.get("CC", "cc"),
                "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                "-I", str(variant_dir),
                "-o", str(binary), str(HARNESS),
            ]
            print("[compile:%s]" % variant, " ".join(compile_cmd))
            proc = subprocess.run(compile_cmd, text=True)
            if proc.returncode != 0:
                print("%s compilation failed" % variant, file=sys.stderr)
                return 2
            result = subprocess.run([str(binary)], text=True)
            if result.returncode != 0:
                return result.returncode
        return 0


if __name__ == "__main__":
    sys.exit(main())
