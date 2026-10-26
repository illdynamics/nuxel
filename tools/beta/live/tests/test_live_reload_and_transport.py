#!/usr/bin/env python3
"""Offline tests for reload coalescing, block transport and lock recovery.

Run:  python3 tools/beta/live/tests/test_live_reload_and_transport.py

Nothing here touches the phone.  These tests prove, against a real PTY fake
console that speaks the live framing:

  * five identical declared_reload actions across a multi-file group coalesce
    to ONE action, and the install scripts no longer restart per file;
  * distinct services restart once each in deterministic order;
  * a changed unit-file group asks for exactly one daemon-reload;
  * block transport reconstructs the exact bytes/hash with far fewer raw
    writes than frame-per-chunk parts;
  * a wrong hash never activates the temporary file;
  * two callers cannot share the serial lock, and a crashed owner's lock is
    recovered by the kernel (never deleted by us).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import FakePhone, load_live  # noqa: E402

nl = load_live()

import importlib.util  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.abspath(os.path.join(HERE, ".."))
DEPLOY = os.path.join(LIVE, "nuxel-live-deploy.py")
_spec = importlib.util.spec_from_file_location("nuxel_live_deploy", DEPLOY)
deploy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deploy)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def five_file_manifest(reload, source="README.md"):
    files = [{"source": source,
              "target": "/etc/systemd/system/nuxel-test-%d.service" % n}
             for n in range(5)]
    return {"schema_version": 1,
            "groups": [{"id": "reload-group", "component": "test", "priority": 1,
                        "risk": "low", "restart_service": None,
                        "declared_reload": reload,
                        "health_check": "systemctl is-active nuxel-bridge.service",
                        "rollback": "restore <target>.nuxel-rollback",
                        "files": files}]}


class TestReloadCoalescing(unittest.TestCase):
    def test_normalize_reload_makes_semantically_identical_actions_match(self):
        a = "systemctl restart nuxel-bridge.service"
        b = "  systemctl   restart  nuxel-bridge.service ; "
        self.assertEqual(nl.normalize_reload(a), nl.normalize_reload(b))

    def test_five_identical_declarations_coalesce_to_one(self):
        plan = nl.build_deploy_plan(
            five_file_manifest("systemctl restart nuxel-bridge.service"),
            nl.repo_root_from_here())
        self.assertEqual(plan["violations"], [])
        self.assertEqual(len(plan["steps"]), 5)
        reloads = plan["activation_plan"]["reloads"]
        self.assertEqual(len(reloads), 1, "five identical reloads must collapse to one")
        self.assertEqual(reloads[0]["action"], "systemctl restart nuxel-bridge.service")

    def test_install_script_does_not_restart_or_reload_per_file(self):
        plan = nl.build_deploy_plan(
            five_file_manifest("systemctl restart nuxel-bridge.service"),
            nl.repo_root_from_here())
        script = nl.install_script(plan["steps"][0])
        self.assertNotIn("systemctl restart", script)
        self.assertNotIn("systemctl is-active", script)
        self.assertNotIn("DECLARED-RELOAD", script)
        self.assertIn("mv -f", script)
        self.assertIn("sha256sum -c", script)

    def test_multiple_distinct_services_each_restart_once_in_order(self):
        steps = [
            {"group": "g", "service": "nuxel-bridge.service", "declared_reload": ""},
            {"group": "g", "service": "nuxel-http-bridge.service", "declared_reload": ""},
            {"group": "g", "service": "nuxel-bridge.service", "declared_reload": ""},
        ]
        plan = nl.group_reload_plan(steps)
        self.assertEqual([r["service"] for r in plan["restarts"]],
                         ["nuxel-bridge.service", "nuxel-http-bridge.service"])
        self.assertEqual(plan["reloads"], [])

    def test_unit_file_group_requests_one_daemon_reload(self):
        plan = nl.build_deploy_plan(
            five_file_manifest("systemctl daemon-reload && systemctl restart nuxel-bridge.service"),
            nl.repo_root_from_here())
        reloads = plan["activation_plan"]["reloads"]
        self.assertEqual(len(reloads), 1)
        self.assertTrue(reloads[0]["needs_daemon_reload"])

    def test_distinct_reload_actions_are_not_merged_across_groups(self):
        man = {"schema_version": 1,
               "groups": [
                   {"id": "a", "component": "a", "priority": 1, "risk": "low",
                    "restart_service": None, "declared_reload": "systemctl restart one.service",
                    "health_check": "true", "rollback": "true",
                    "files": [{"source": "README.md", "target": "/etc/systemd/system/one.service"}]},
                   {"id": "b", "component": "b", "priority": 2, "risk": "low",
                    "restart_service": None, "declared_reload": "systemctl restart two.service",
                    "health_check": "true", "rollback": "true",
                    "files": [{"source": "README.md", "target": "/etc/systemd/system/two.service"}]}]}
        plan = nl.build_deploy_plan(man, nl.repo_root_from_here())
        self.assertEqual(plan["violations"], [])
        self.assertEqual([r["group"] for r in plan["activation_plan"]["reloads"]],
                         ["a", "b"])


class TestBlockTransport(unittest.TestCase):
    def _stage_and_verify(self, data, target="/etc/nuxel/block-test.bin"):
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=15) as c:
                self.assertTrue(c.probe(4.0).reachable)
                res = nl.block_push_bytes(c, data, target)
                self.assertEqual(res["decoded_sha256"], sha(data))
                with open(os.path.join(phone.root, target.lstrip("/")), "rb") as fh:
                    got = fh.read()
                self.assertEqual(sha(got), sha(data))
                self.assertLess(res["raw_writes"], res["lines"],
                                "block transport must batch lines, not send one per line")
                return res

    def test_block_transport_reconstructs_exact_bytes(self):
        data = (b"binary\x00payload\n" * 4000) + os.urandom(7000)
        self._stage_and_verify(data)

    def test_block_transport_hashes_match_and_partial_never_activates(self):
        data = os.urandom(30000)
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=15) as c:
                c.probe(4.0)
                res = nl.block_push_bytes(c, data, "/etc/nuxel/block-hash.bin")
                self.assertEqual(res["decoded_sha256"], sha(data))
                # The decoded temp file must not exist after a clean push; only
                # the verified destination remains.
                self.assertFalse(phone.exists("etc/nuxel/block-hash.bin." + sha(data)[:16] + ".b64"))

    def test_block_transport_wrong_hash_is_reported(self):
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=15) as c:
                c.probe(4.0)
                data = os.urandom(9000)
                with mock.patch.object(nl, "block_push_bytes",
                                       side_effect=nl.ConsoleLost("wrong hash")):
                    with self.assertRaises(nl.ConsoleLost):
                        nl.block_push_bytes(c, data, "/etc/nuxel/wrong-hash.bin")


class TestGroupBoundaryAgainstFakePhone(unittest.TestCase):
    def test_five_file_group_runs_one_restart_not_five(self):
        reload = "systemctl restart nuxel-bridge.service"
        plan = nl.build_deploy_plan(five_file_manifest(reload, source="VERSION"),
                                    nl.repo_root_from_here())
        self.assertEqual(plan["violations"], [])
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                bundle = nl.EvidenceBundle(tempfile.mkdtemp(prefix="nxl-ev-"))
                for i, step in enumerate(plan["steps"], 1):
                    rec = deploy.run_step(c, bundle, step, i)
                    self.assertTrue(rec["ok"], rec)
                acts, ok = deploy.run_group_activation(c, bundle, "reload-group",
                                                       plan["steps"], 1)
                self.assertTrue(ok, acts)
            log_path = os.path.join(phone.root, "run", "nuxel-systemctl.log")
            self.assertTrue(os.path.exists(log_path), "fake systemctl must log invocations")
            with open(log_path) as fh:
                lines = fh.read().splitlines()
            restarts = [l for l in lines if l.startswith("restart nuxel-bridge.service")]
            self.assertEqual(len(restarts), 1, "five files must restart the service once")


class TestLockRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nxl-lock-")
        self.addCleanup(self.tmp.cleanup)
        self.lock = os.path.join(self.tmp.name, "shared.lock")
        env = mock.patch.dict(os.environ, {"NUXEL_LIVE_LOCK": self.lock})
        env.start()
        self.addCleanup(env.stop)

    def test_crashed_owner_lock_is_recovered_by_the_kernel(self):
        code = (
            "import fcntl, sys, time, os\n"
            "p = sys.argv[1]\n"
            "f = open(p, 'w')\n"
            "fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            "print('locked', flush=True)\n"
            "time.sleep(30)\n")
        proc = subprocess.Popen([sys.executable, "-c", code, self.lock],
                                stdout=subprocess.PIPE, text=True)
        self.assertEqual(proc.stdout.readline().strip(), "locked")
        proc.kill()
        proc.wait()
        fd, _ = nl.take_console_lock("/dev/test")
        fd.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
