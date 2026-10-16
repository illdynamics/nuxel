#!/usr/bin/env python3
"""harness — spin up a fake Nuxel console on a temp fake root for offline tests.

Nothing here is device evidence.  It exists so every line of the live tooling
(baseline capture, staged deploy + rollback, reboot policy) is *executed*
against a real PTY that speaks the real framing before the phone is available.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.abspath(os.path.join(HERE, ".."))
FAKE = os.path.join(HERE, "fake_console.py")


class FakePhone:
    """Context manager: `with FakePhone("healthy") as phone: phone.dev`."""

    def __init__(self, mode="healthy", workdir=None, timeout=30.0):
        self.mode = mode
        self.workdir = workdir or tempfile.mkdtemp(prefix="nxl-fake-")
        self.root = os.path.join(self.workdir, "root")
        self.ready = os.path.join(self.workdir, "ready.txt")
        self.timeout = timeout
        self.proc = None
        self.dev = None

    def __enter__(self):
        os.makedirs(self.root, exist_ok=True)
        self.proc = subprocess.Popen(
            [sys.executable, FAKE, "--root", self.root, "--mode", self.mode,
             "--ready-file", self.ready, "--seconds", "900"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        t0 = time.time()
        while time.time() - t0 < self.timeout:
            if os.path.exists(self.ready) and os.path.getsize(self.ready) > 0:
                with open(self.ready) as fh:
                    self.dev = fh.read().strip()
                if self.dev and os.path.exists(self.dev):
                    return self
            if self.proc.poll() is not None:
                err = self.proc.stderr.read().decode() if self.proc.stderr else ""
                raise RuntimeError("fake console died: %s" % err)
            time.sleep(0.1)
        raise RuntimeError("fake console never became ready")

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        return False

    def destroy(self):
        shutil.rmtree(self.workdir, ignore_errors=True)

    # convenience passthroughs for assertions
    def read(self, rel):
        with open(os.path.join(self.root, rel.lstrip("/"))) as fh:
            return fh.read()

    def exists(self, rel):
        return os.path.exists(os.path.join(self.root, rel.lstrip("/")))

    def json(self, rel):
        return json.loads(self.read(rel))


def load_live():
    """Import nuxel_live from tools/beta/live without polluting sys.path order."""
    if LIVE not in sys.path:
        sys.path.insert(0, LIVE)
    import nuxel_live as nl  # noqa: E402
    return nl
