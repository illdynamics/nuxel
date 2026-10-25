#!/usr/bin/env python3
"""Run the phone host indicator harness against the real source block.

Extracts the sensor section from tools/s10plus/a45/nuxel-pwa-host.c and compiles
tools/s10plus/a45/test-lockscreen-indicators.c against it.  No GTK, no device.

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
SOURCE = HERE / "nuxel-pwa-host.c"
HARNESS = HERE / "test-lockscreen-indicators.c"


def extract_sensor_block(text: str) -> str:
    start = text.index("/* ============================================================================\n * Lockhead indicators")
    end = text.index("/* Event-driven refresh:", start)
    return text[start:end]


def main() -> int:
    snippet = extract_sensor_block(SOURCE.read_text())
    with tempfile.TemporaryDirectory(prefix="nuxel-ind-c-") as work:
        workdir = Path(work)
        (workdir / "indicator_snippet.inc").write_text(snippet)
        binary = workdir / "test-lockscreen-indicators"
        compile_cmd = [
            os.environ.get("CC", "cc"),
            "-std=gnu11", "-Wall", "-Wextra", "-Werror",
            "-I", str(workdir),
            "-o", str(binary), str(HARNESS),
        ]
        print("[compile]", " ".join(compile_cmd))
        proc = subprocess.run(compile_cmd, text=True)
        if proc.returncode != 0:
            print("compilation failed", file=sys.stderr)
            return 2
        return subprocess.run([str(binary)], text=True).returncode


if __name__ == "__main__":
    sys.exit(main())
