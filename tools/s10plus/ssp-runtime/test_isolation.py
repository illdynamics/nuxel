#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from run_isolated import sandbox, verify


class IsolationTests(unittest.TestCase):
    def test_rejects_unlisted_files_and_internal_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "library.so").write_bytes(b"original")
            good = {"library.so": hashlib.sha256(b"original").hexdigest()}
            (root / "sha256-manifest.json").write_text(json.dumps(good))
            (root / "ld.config.txt").write_text("unreviewed")
            with self.assertRaisesRegex(ValueError, "unlisted"):
                verify(root)
            (root / "ld.config.txt").unlink()
            (root / "alias.so").symlink_to("library.so")
            good["alias.so"] = good["library.so"]
            (root / "sha256-manifest.json").write_text(json.dumps(good))
            with self.assertRaisesRegex(ValueError, "symlink"):
                verify(root)

    def test_rejects_unlisted_fifo_and_directory_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "file").write_bytes(b"data")
            (root / "sha256-manifest.json").write_text(json.dumps(
                {"file": hashlib.sha256(b"data").hexdigest()}))
            os.mkfifo(root / "pipe")
            with self.assertRaisesRegex(ValueError, "special"):
                verify(root)
            (root / "pipe").unlink()
            (root / "subdir").mkdir()
            (root / "alias").symlink_to("subdir", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                verify(root)

    def test_namespace_device_and_capability_contract(self):
        cmd = sandbox(Path("/owner/runtime"), "/bwrap")
        for flag in ("--unshare-all", "--die-with-parent", "--new-session", "--clearenv"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--cap-drop") + 1], "ALL")
        self.assertEqual(cmd[cmd.index("--uid") + 1], "65534")
        self.assertNotIn("--share-net", cmd)
        self.assertNotIn("--bind", cmd)
        self.assertNotIn("--dev-bind", cmd)
        self.assertEqual(cmd.count("--ro-bind"), 1)
        self.assertEqual(cmd[cmd.index("--ro-bind") + 1:cmd.index("--ro-bind") + 3],
                         ["/owner/runtime", "/"])
        self.assertEqual(cmd[cmd.index("--dev") + 1], "/dev")
        self.assertEqual(cmd[-2:], ["/vendor/bin/hw/lhd", "/vendor/etc/sensor/lhd-isolated.conf"])

    def test_probe_uses_identical_isolation(self):
        normal = sandbox(Path("/runtime"), "/bwrap")
        probe = sandbox(Path("/runtime"), "/bwrap", True)
        self.assertEqual(normal[:-2], probe[:-1])

    def test_only_fresh_log_directory_can_be_written(self):
        cmd = sandbox(Path("/runtime"), "/bwrap", logs=Path("/run/trial/logs"))
        self.assertEqual(cmd.count("--bind"), 1)
        self.assertEqual(cmd[cmd.index("--bind") + 1:cmd.index("--bind") + 3],
                         ["/run/trial/logs", "/logs"])

    def test_hashes_tampering_and_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data = root / "library.so"
            data.write_bytes(b"original")
            manifest = root / "sha256-manifest.json"
            good = {"library.so": hashlib.sha256(data.read_bytes()).hexdigest()}
            manifest.write_text(json.dumps(good))
            self.assertEqual(verify(root), good)
            data.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                verify(root)
            for path in ("../outside", "/etc/shadow"):
                manifest.write_text(json.dumps({path: "0" * 64}))
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    verify(root)
            (root / "outside").symlink_to("/etc/passwd")
            manifest.write_text(json.dumps({"outside": "0" * 64}))
            with self.assertRaisesRegex(ValueError, "escaping"):
                verify(root)


if __name__ == "__main__":
    unittest.main()
