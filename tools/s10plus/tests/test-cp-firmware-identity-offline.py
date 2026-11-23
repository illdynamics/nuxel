#!/usr/bin/env python3
"""Offline CI entry-point for the CP artifact analyzer suite.

Delegates to tools/s10plus/cp-firmware/tests/test_analyze_cp_artifact.py.
Fixtures are generated in a temp dir and removed; no real firmware is read.
Run:  python3 tools/s10plus/tests/test-cp-firmware-identity-offline.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITE = os.path.join(HERE, "..", "cp-firmware", "tests", "test_analyze_cp_artifact.py")

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, SUITE]))
