#!/usr/bin/env python3
"""Offline tests for the live-console library (briq-10a/10b/10c).

Run:  python3 tools/beta/live/tests/test_live_lib.py
These tests NEVER touch the phone.  They prove:
  * capability selection never hard-codes a tty node name;
  * the flash-free guards refuse partition/kernel/modem paths and flash tooling;
  * the shell framing round-trips a real command over a PTY with a verified
    SHA-256 (this is the test that caught the B/R body-parse mismatch);
  * a silent far end is reported as unreachable, not as success;
  * the deploy plan maps each target to the single smallest service and refuses
    a plan whose manifest points at a raw partition;
  * the reboot policy refuses blind repeats / unrecovered reboots;
  * the host serialisation lock is taken on the SHARED /tmp path when this uid
    can use it, reopens the same inode without O_CREAT for protected_regular,
    and refuses inaccessible locks instead of bypassing an active peer.
"""

from __future__ import annotations
from unittest import mock
import subprocess
from pathlib import Path

import contextlib
import fcntl
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import FakePhone, load_live  # noqa: E402

nl = load_live()


class TestCapabilitySelection(unittest.TestCase):
    def test_ioreg_nodes_parsed_and_selected_without_node_name(self):
        text = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "..", "..", "..", "docs", "beta-finalization",
                                 "live", "evidence", "reachability-20261016",
                                 "host-ioreg-acm.txt")).read()
        nodes = nl.parse_ioreg_acm(text)
        self.assertTrue(nodes, "ioreg fixture must yield a node")
        node = nl.select_console_node(nodes, vid=0x18D1, pid=0x4EE7)
        self.assertEqual(node["tty_suffix"], "201")
        self.assertIn("vid+pid", node["match_stage"])

    def test_wrong_vid_is_a_selection_error_not_a_guess(self):
        nodes = [{"callout": "/dev/cu.usbserial-1420", "vid": 0x0403, "pid": 0x6001,
                  "tty_base": "usbserial", "tty_device": "usbserial-1420"}]
        with self.assertRaises(nl.SelectionError):
            nl.select_console_node(nodes)

    def test_ambiguous_console_is_refused(self):
        nodes = [{"callout": "/dev/cu.usbmodem1", "vid": 0x18D1, "pid": 0x4EE7,
                  "tty_base": "usbmodem", "tty_device": "usbmodem1"},
                 {"callout": "/dev/cu.usbmodem2", "vid": 0x18D1, "pid": 0x4EE7,
                  "tty_base": "usbmodem", "tty_device": "usbmodem2"}]
        with self.assertRaises(nl.SelectionError):
            nl.select_console_node(nodes)


class TestFlashFreeGuards(unittest.TestCase):
    def test_partition_and_boot_paths_are_refused(self):
        for p in ("/dev/block/by-name/BOOT", "/dev/block/mmcblk0p10",
                  "/dev/disk/by-partlabel/recovery", "/boot/vmlinuz",
                  "/etc/nuxel/modem/nvdata.bin", "/home/nuxel/nuxel/x.dtb",
                  "/dev/fb0", "/sys/class/graphics"):
            with self.assertRaises(nl.GuardViolation, msg="must refuse %s" % p):
                nl.assert_userspace_path(p)

    def test_userspace_targets_are_allowed(self):
        for p in ("/home/nuxel/nuxel/pwa/nuxel-home/index.html",
                  "/etc/nuxel/button/gestures.conf", "/usr/local/bin/nuxel-wl-fb",
                  "/etc/systemd/system/nuxel-pwa.service"):
            self.assertEqual(nl.assert_userspace_path(p), os.path.normpath(p))

    def test_flash_tooling_is_refused_in_commands(self):
        for c in ("heimdall flash --BOOT boot.img", "odin4 -b BL", "dd if=/dev/block/mmcblk0"):
            with self.assertRaises(nl.GuardViolation):
                nl.assert_no_flash_tooling(c)

    def test_qq_paths_are_never_written(self):
        with self.assertRaises(nl.GuardViolation):
            nl.ensure_not_qq("/Users/wicked/x/nuxel/.qq/runs/x/receipt.json")


class TestFramingOverPty(unittest.TestCase):
    def test_framed_command_round_trips_with_verified_sha(self):
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=15) as c:
                probe = c.probe(4.0)
                self.assertTrue(probe.reachable, "fake console must answer a CR")
                res = c.run("id")
                self.assertTrue(res.ok, "frame must verify (framed=%s sha=%s)"
                                % (res.framed, res.sha_ok))
                self.assertEqual(res.rc, 0)
                self.assertIn("uid=0(root)", res.output)

    def test_device_paths_are_read_through_the_frame(self):
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=15) as c:
                res = c.run("cat /var/lib/nuxel/fb-owner")
                self.assertTrue(res.ok)
                self.assertEqual(res.output.strip(), "nuxel-wl-fb")
                res = c.run("grep -i madera /proc/asound/cards")
                self.assertTrue(res.ok)
                self.assertIn("beyond-madera", res.output)

    def test_silent_far_end_is_unreachable_not_success(self):
        with FakePhone("silent") as phone:
            with nl.Console(phone.dev, timeout=6) as c:
                probe = c.probe(2.0)
                self.assertFalse(probe.reachable)
                res = c.run("id", timeout=3)
                self.assertFalse(res.ok)

    def test_unframed_far_end_never_reports_ok(self):
        with FakePhone("frame-broken") as phone:
            with nl.Console(phone.dev, timeout=6) as c:
                res = c.run("id", timeout=4)
                self.assertFalse(res.ok, "an unframed reply must never look like success")

    def test_long_wrapped_command_is_refused(self):
        # The ceiling is the tty line buffer (nl.MAX_WRAPPER_LEN), not a fixed
        # 480: a wrapped command past it must still be refused.
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=10) as c:
                with self.assertRaises(nl.GuardViolation):
                    c.run("echo " + "x" * (nl.MAX_WRAPPER_LEN + 400))


class TestDeployPlanning(unittest.TestCase):
    def _manifest(self, target, source):
        return {"groups": [{"id": "g1", "component": "launcher", "priority": 2,
                            "restart_service": None,
                            "files": [{"source": source, "target": target}]}]}

    def test_smallest_service_mapping(self):
        self.assertEqual(nl.smallest_service_for("/home/nuxel/nuxel/pwa/nuxel-home/index.html"),
                         "nuxel-pwa")
        self.assertEqual(nl.smallest_service_for("/etc/nuxel/button/gestures.conf"),
                         "nuxel-button-manager")
        self.assertEqual(nl.smallest_service_for("/usr/local/bin/nuxel-wl-fb"),
                         "nuxel-wl-fb")
        self.assertIsNone(nl.smallest_service_for("/etc/xdg/somerc"))

    def test_plan_refuses_partition_target(self):
        repo = nl.repo_root_from_here()
        man = self._manifest("/dev/block/by-name/BOOT", "README.md")
        plan = nl.build_deploy_plan(man, repo)
        self.assertFalse(plan["steps"])
        self.assertTrue(any(v["kind"] == "guard" for v in plan["violations"]))

    def test_plan_flags_missing_staged_source(self):
        plan = nl.build_deploy_plan(self._manifest("/etc/nuxel/x.conf", "does/not/exist"),
                                    nl.repo_root_from_here())
        self.assertTrue(any(v["kind"] == "missing_source" for v in plan["violations"]))

    def test_declared_blocked_group_is_skipped_not_written(self):
        man = {"groups": [{"id": "kernel-bit", "state": "blocked_kernel",
                           "blocked_reason": "needs a new kernel image",
                           "files": [{"source": "README.md",
                                      "target": "/etc/nuxel/x.conf"}]}]}
        plan = nl.build_deploy_plan(man, nl.repo_root_from_here())
        self.assertFalse(plan["steps"])
        self.assertFalse(plan["violations"])
        self.assertEqual(plan["skipped"][0]["verdict"], "BLOCKED_KERNEL")

    def test_install_script_has_stage_verify_install_restart_and_rollback(self):
        step = {"source_sha256": "a" * 64, "target": "/etc/nuxel/touch/touch.conf",
                "staged": "/etc/nuxel/touch/touch.conf.nuxel-staged",
                "backup": "/etc/nuxel/touch/touch.conf.nuxel-rollback",
                "service": "nuxel-touch-arm", "verify": "sha256sum /etc/nuxel/touch/touch.conf"}
        script = nl.install_script(step)
        for needle in ("sha256sum -c", "mv -f", "systemctl restart nuxel-touch-arm",
                       "systemctl is-active nuxel-touch-arm", "rollback"):
            self.assertIn(needle, script)
        self.assertNotIn("/dev/block", script)


class TestRebootPolicy(unittest.TestCase):
    def test_first_reboot_allowed_with_reason_and_diagnostic(self):
        pol = nl.RebootPolicy()
        hist = []
        v = pol.next_reboot(hist)
        self.assertTrue(v["allowed"])
        pol.record(hist, "apply staged userspace deploy", "post-boot fb-owner probe",
                   returned_to_nuxel=True)
        self.assertEqual(len(hist), 1)

    def test_blind_repeat_is_refused(self):
        pol = nl.RebootPolicy()
        hist = []
        pol.record(hist, "reason A", "diagnostic A", returned_to_nuxel=True)
        with self.assertRaises(nl.GuardViolation):
            pol.record(hist, "reason B", "diagnostic A", returned_to_nuxel=True)
        with self.assertRaises(nl.GuardViolation):
            pol.record(hist, "reason A", "diagnostic B", returned_to_nuxel=True)

    def test_unrecovered_reboot_blocks_the_next_one(self):
        pol = nl.RebootPolicy()
        hist = []
        pol.record(hist, "reason A", "diag A", returned_to_nuxel=False)
        v = pol.next_reboot(hist)
        self.assertFalse(v["allowed"])
        self.assertEqual(v["code"], "not_recovered")

    def test_budget_is_bounded(self):
        pol = nl.RebootPolicy(max_reboots=2)
        hist = []
        pol.record(hist, "r1", "d1", returned_to_nuxel=True)
        pol.record(hist, "r2", "d2", returned_to_nuxel=True)
        v = pol.next_reboot(hist)
        self.assertFalse(v["allowed"])
        self.assertEqual(v["code"], "budget_exhausted")

    def test_missing_rollback_blocks_the_next_reboot(self):
        pol = nl.RebootPolicy()
        hist = []
        pol.record(hist, "r1", "d1", returned_to_nuxel=True, rollback_known_good=False)
        v = pol.next_reboot(hist)
        self.assertFalse(v["allowed"])
        self.assertEqual(v["code"], "no_rollback")


class TestBaselineProbeSet(unittest.TestCase):
    def test_baseline_probes_cover_every_required_area(self):
        keys = [k for k, _ in nl.baseline_probes(["pwa/nuxel-home/index.html"])]
        for needle in ("uptime", "boot_mode", "units", "failed_units", "fb_owner",
                       "animation", "wl_fb_state", "touch_devices", "alsa_cards",
                       "alsa_beyond_madera", "irq_sec_ts", "http_registry",
                       "pwa_sha256:pwa/nuxel-home/index.html"):
            self.assertIn(needle, keys)

    def test_every_probe_fits_the_console_line_budget(self):
        for key, cmd in nl.baseline_probes(["pwa/nuxel-home/index.html",
                                            "pwa/nuxel-home/js/apps.js"]):
            # the wrapper adds ~250 chars; the probe itself must stay small
            self.assertLess(len(cmd), nl.MAX_WRAPPER_LEN - 200, "probe %s too long" % key)


class TestEvidenceBundle(unittest.TestCase):
    def test_bundle_writes_manifest_without_qq(self):
        import tempfile
        d = tempfile.mkdtemp(prefix="nxl-ev-")
        b = nl.EvidenceBundle(d, name="unit", label="unit")
        b.write("a.txt", "hello")
        b.write_json("b.json", {"k": 1})
        man, lines = b.manifest()
        self.assertTrue(os.path.exists(man))
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(len(l.split()[0]) == 64 for l in lines))


class TestConsoleLock(unittest.TestCase):
    """Shared-inode exclusion survives Fedora protected_regular and failures."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nxl-locktest-")
        self.addCleanup(self.tmp.cleanup)
        self.shared = os.path.join(self.tmp.name, "shared.lock")
        env = mock.patch.dict(os.environ, {"NUXEL_LIVE_LOCK": self.shared})
        env.start()
        self.addCleanup(env.stop)

    def protected_open(self, path, mode):
        if mode == "a+":
            raise PermissionError("protected_regular denies O_CREAT")
        return open(path, mode)

    def test_shared_lock_excludes_peer_and_releases(self):
        fd, path = nl.take_console_lock("/dev/test")
        try:
            self.assertEqual(path, self.shared)
            with self.assertRaisesRegex(nl.ConsoleLost, "owned by another host tool"):
                nl.take_console_lock("/dev/test")
        finally:
            fd.close()
        fd, _ = nl.take_console_lock("/dev/test")
        fd.close()

    def test_protected_regular_reopens_same_inode_without_truncating(self):
        Path(self.shared).write_text("owner metadata")
        before = os.stat(self.shared).st_ino
        fd, path = nl.take_console_lock("/dev/test", opener=self.protected_open)
        try:
            self.assertEqual(path, self.shared)
            self.assertEqual(os.fstat(fd.fileno()).st_ino, before)
            self.assertEqual(Path(path).read_text(), "owner metadata")
        finally:
            fd.close()

    def test_protected_regular_never_bypasses_active_peer(self):
        fd, _ = nl.take_console_lock("/dev/test")
        try:
            with self.assertRaisesRegex(nl.ConsoleLost, "owned by another host tool"):
                nl.take_console_lock("/dev/test", opener=self.protected_open)
            self.assertEqual(os.listdir(self.tmp.name), ["shared.lock"])
        finally:
            fd.close()

    def test_unreadable_shared_lock_fails_closed(self):
        with self.assertRaisesRegex(nl.ConsoleLost, "refusing to share"):
            nl.take_console_lock("/dev/test", opener=mock.Mock(side_effect=PermissionError()))
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_failed_port_open_releases_lock(self):
        with mock.patch.object(nl.os, "open", side_effect=PermissionError("serial denied")):
            with self.assertRaises(nl.ConsoleLost):
                nl.Console("/dev/test").open()
        fd, _ = nl.take_console_lock("/dev/test")
        fd.close()

    def test_shell_transport_obeys_same_held_lock_before_opening_port(self):
        fd, _ = nl.take_console_lock("/dev/test")
        try:
            root = Path(__file__).resolve().parents[4]
            result = subprocess.run(["bash", str(root / "scripts/s10plus-debug-pack/nuxel-live.sh"),
                                     "--dev", "/dev/test", "--run", "id"],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIn("owned by another host tool", result.stderr)
        finally:
            fd.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
