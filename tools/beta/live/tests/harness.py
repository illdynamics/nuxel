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
        self.workdirs = []

    def __enter__(self):
        self.spawn()
        return self

    def spawn(self, mode=None, workdir=None, timeout=None):
        """Start a console (fresh fake root) and return its node path."""
        mode = mode or self.mode
        if workdir:
            self.workdir = workdir
            self.root = os.path.join(self.workdir, "root")
            self.ready = os.path.join(self.workdir, "ready.txt")
        os.makedirs(self.root, exist_ok=True)
        self.workdirs.append(self.workdir)
        self.proc = subprocess.Popen(
            [sys.executable, FAKE, "--root", self.root, "--mode", mode,
             "--ready-file", self.ready, "--seconds", "900"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        t0 = time.time()
        deadline = t0 + (timeout or self.timeout)
        while time.time() < deadline:
            if os.path.exists(self.ready) and os.path.getsize(self.ready) > 0:
                with open(self.ready) as fh:
                    self.dev = fh.read().strip()
                if self.dev and os.path.exists(self.dev):
                    self.mode = mode
                    return self.dev
            if self.proc.poll() is not None:
                err = self.proc.stderr.read().decode() if self.proc.stderr else ""
                raise RuntimeError("fake console died: %s" % err)
            time.sleep(0.1)
        raise RuntimeError("fake console never became ready")

    def restart_after_reboot(self, dev_file, mode="post-reboot", timeout=60.0):
        """Wait for the running console to power-cycle, then come back up.

        Models the USB CDC-ACM re-enumeration after a reboot: the old PTY dies, a
        *new* one appears, and the node file the host tool polls is republished —
        which is why the tool may never assume a fixed node name.
        """
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.proc.poll() is not None:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("the fake console never power-cycled")
        if self.proc.stderr:
            self.proc.stderr.close()
        if self.proc.stdout:
            self.proc.stdout.close()
        dev = self.spawn(mode, workdir=tempfile.mkdtemp(prefix="nxl-fake-"))
        with open(dev_file, "w") as fh:
            fh.write(dev + "\n")
        return dev

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        return False

    def destroy(self):
        for d in set(self.workdirs):
            shutil.rmtree(d, ignore_errors=True)

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
