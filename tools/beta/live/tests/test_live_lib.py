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
    can use it, falls back to the private per-uid path (nuxel-live.sh semantics)
    when it cannot, and refuses a port another host tool already owns either way.
"""

from __future__ import annotations

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
    """The one-host-tool-per-port lock (briq-00-lock-fallback-fix).

    The defect this class is the regression test for: the live console always runs
    through sudo, and `open(path, "w")` on a /tmp lock file owned by another uid
    raises PermissionError on a host with fs.protected_regular=2 (Fedora default).
    scripts/s10plus-debug-pack/nuxel-live.sh already fell back to a private per-uid
    lock; nuxel_live.py did not, so root could not take the shared lock at all.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nxl-locktest-")
        self._env = {k: os.environ.get(k) for k in ("TMPDIR", "NUXEL_LIVE_LOCK")}
        os.environ["TMPDIR"] = self.tmp
        os.environ.pop("NUXEL_LIVE_LOCK", None)
        self._orig_shared = nl._shared_lock_path
        self._orig_private = nl._private_lock_path

    def tearDown(self):
        nl._shared_lock_path = self._orig_shared
        nl._private_lock_path = self._orig_private
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    # -- helpers ------------------------------------------------------------ #
    @staticmethod
    def _dir_as_lock(path):
        """Hand `path` back as a *directory*: open(path, "w") is then an OSError
        for every uid (IsADirectoryError), which is exactly the class of failure
        the shared /tmp lock hits when it is owned by another uid under sudo.
        Deterministic even when the suite runs as root, unlike a chmod."""
        os.makedirs(path, exist_ok=True)
        return path

    def test_shared_lock_is_taken_when_the_uid_can_use_it(self):
        shared = os.path.join(self.tmp, "shared.lock")
        os.environ["NUXEL_LIVE_LOCK"] = shared
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=15) as first:
                self.assertEqual(first.lock_path, shared)
                self.assertTrue(os.path.exists(shared))
                # a real flock, not merely an open file: a second connection in
                # this very process is refused while the first one holds it
                with self.assertRaises(nl.ConsoleLost) as ctx:
                    with nl.Console(phone.dev, timeout=15, lock_wait=0.0):
                        pass
                self.assertIn("owned by another host tool", str(ctx.exception))
                self.assertIn(shared, str(ctx.exception))
            # ... and the lock is released on close, so the next tool may take it
            with nl.Console(phone.dev, timeout=15) as third:
                self.assertEqual(third.lock_path, shared)

    def test_held_shared_lock_is_reported_as_held_not_as_a_fallback(self):
        dev = "/dev/ttyACM-lockheld0"
        shared = os.path.join(self.tmp, "held.lock")
        os.environ["NUXEL_LIVE_LOCK"] = shared
        fd = nl._flock(shared, 0.0)
        try:
            with self.assertRaises(nl.ConsoleLost) as ctx:
                nl.take_console_lock(dev, lock_wait=0.0)
            self.assertIn("owned by another host tool", str(ctx.exception))
            self.assertIn(shared, str(ctx.exception))
            # a held lock is NOT a permission problem: no fallback is created
            self.assertFalse(os.path.exists(nl._private_lock_path(dev)),
                             "a genuinely held lock must never be bypassed")
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            fd.close()

    def test_unopenable_shared_lock_falls_back_to_the_private_per_uid_lock(self):
        dev = "/dev/ttyACM-fallback0"
        nl._shared_lock_path = lambda d: self._dir_as_lock(
            os.path.join(self.tmp, "shared-is-a-directory"))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            fd, path = nl.take_console_lock(dev, lock_wait=0.0)
        try:
            private = nl._private_lock_path(dev)
            self.assertEqual(path, private)
            self.assertTrue(os.path.exists(private))
            self.assertIn(private, err.getvalue())
            self.assertIn("# shared lock", err.getvalue())
            self.assertIn("— using private lock", err.getvalue())
            self.assertIn("uid %d" % os.getuid(), err.getvalue())
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            fd.close()

    def test_private_lock_still_excludes_a_second_connection(self):
        dev = "/dev/ttyACM-fallback1"
        nl._shared_lock_path = lambda d: self._dir_as_lock(
            os.path.join(self.tmp, "shared-is-a-directory"))
        fd, path = nl.take_console_lock(dev, lock_wait=0.0)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(nl.ConsoleLost) as ctx:
                    nl.take_console_lock(dev, lock_wait=0.0)
            self.assertIn("owned by another host tool", str(ctx.exception))
            self.assertIn(path, str(ctx.exception))
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            fd.close()

    def test_shared_path_shape_mirrors_nuxel_live_sh(self):
        os.environ.pop("NUXEL_LIVE_LOCK", None)
        self.assertEqual(nl._shared_lock_path("/dev/ttyACM0"),
                         "/tmp/nuxel-live._dev_ttyACM0.lock")
        self.assertEqual(nl._private_lock_path("/dev/ttyACM0"),
                         "%s/nuxel-live._dev_ttyACM0.%d.lock" % (self.tmp, os.getuid()))
        # ... and the two are different files, so the fallback never aliases the
        # shared lock it could not open (that would defeat the mutual exclusion)
        self.assertNotEqual(nl._shared_lock_path("/dev/ttyACM0"),
                            nl._private_lock_path("/dev/ttyACM0"))

    def test_both_paths_unusable_is_a_refusal_not_a_silent_share(self):
        dev = "/dev/ttyACM-hopeless"
        nl._shared_lock_path = lambda d: self._dir_as_lock(os.path.join(self.tmp, "d1"))
        nl._private_lock_path = lambda d, uid=None: self._dir_as_lock(
            os.path.join(self.tmp, "d2"))
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(nl.ConsoleLost) as ctx:
                nl.take_console_lock(dev, lock_wait=0.0)
        self.assertIn("cannot take a port lock", str(ctx.exception))
        self.assertIn("refusing to share the serial port", str(ctx.exception))

    def test_fallback_does_not_typeerror_on_a_console(self):
        """The Console path (not just the helper) must survive the fallback, so a
        sudo session can serialise the port end to end."""
        with FakePhone("healthy") as phone:
            nl._shared_lock_path = lambda d: self._dir_as_lock(
                os.path.join(self.tmp, "shared-is-a-directory"))
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                c = nl.Console(phone.dev, timeout=15)
                c.open()
            try:
                self.assertTrue(c.lock_path.startswith(self.tmp))
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(nl.ConsoleLost):
                        nl.Console(phone.dev, timeout=15, lock_wait=0.0).open()
            finally:
                c.close()
            self.assertIn("using private lock", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
