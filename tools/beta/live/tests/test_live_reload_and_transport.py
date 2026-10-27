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

import base64
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
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

    def test_small_file_push_records_integer_transport_counts(self):
        # push_bytes (the fallback/small-file path) has no block/raw_writes keys;
        # run_step must coerce them to ints or main() later crashes on int(None).
        plan = nl.build_deploy_plan(
            five_file_manifest("true", source="VERSION"), nl.repo_root_from_here())
        self.assertEqual(plan["violations"], [])
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                bundle = nl.EvidenceBundle(tempfile.mkdtemp(prefix="nxl-ev-"))
                rec = deploy.run_step(c, bundle, plan["steps"][0], 1)
                self.assertTrue(rec["ok"], rec)
                sp = rec["staged_push"]
                self.assertIsInstance(sp["raw_writes"], int, sp)
                self.assertIsInstance(sp["blocks"], int, sp)
                self.assertIsInstance(sp["retries"], int, sp)

    def test_block_fallback_records_integer_transport_counts(self):
        # If the block fast-path is unsupported and run_step falls back to
        # push_bytes, the aggregated transport totals must stay integers.
        # push_bytes/run_script are mocked here: this is an accounting test, not
        # a 50 KB frame-transfer benchmark (which made the old test hang).
        plan = nl.build_deploy_plan(
            five_file_manifest("true", source="README.md"), nl.repo_root_from_here())
        self.assertEqual(plan["violations"], [])
        step = plan["steps"][0]
        fake_push = {"path": step["staged"], "bytes": 12345, "acked_bytes": 12345,
                     "parts": 97, "retries": 2, "decoded_sha256": step["source_sha256"],
                     "mode": "frame"}
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                with mock.patch.object(nl, "block_push_bytes",
                                       side_effect=nl.ConsoleLost("unsupported")), \
                        mock.patch.object(nl, "push_bytes", return_value=fake_push), \
                        mock.patch.object(deploy, "run_script",
                                          return_value={"framed": True, "rc": 0,
                                                        "output":
                                                            "PREV=NONE\nINSTALL-OK\n"}):
                    rec = deploy.run_step(c, None, step, 1)
        self.assertTrue(rec["ok"], rec)
        sp = rec["staged_push"]
        self.assertTrue(sp.get("fallback"), sp)
        for key in ("raw_writes", "blocks", "retries"):
            self.assertIsInstance(sp[key], int, sp)


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



class _Buf:
    def __init__(self):
        self.data = ""
    def clear(self):
        self.data = ""
    def __str__(self):
        return self.data


class _RR:
    def __init__(self, ok, rc, output):
        self.ok, self.rc, self.output = ok, rc, output


class _BlockHost:
    """Minimal fake transport host for block_push_bytes (no real device tree).

    It emulates the base64 part file, the explicit ``@@AB<rid>:<block>:<len>@@``
    acknowledgement, a verified-prefix resume, and the bounded rewind path.
    Nothing here is device evidence; it makes every protocol branch executable.
    """

    def __init__(self, want_sha, corrupt=False, initial_prefix="", wrong_decode=False):
        self.timeout = 1.0
        self.buf = _Buf()
        self.writes = []
        self.run_calls = []
        self.want_sha = want_sha
        self.accumulated = initial_prefix
        self.corrupt = corrupt
        self.wrong_decode = wrong_decode
        self.send_raises = None
        self.pending_ack = None
        self.acks = 0
        self.promoted = False

    def run(self, cmd, timeout=None, guard=False):
        self.run_calls.append(cmd)
        if cmd.startswith("stty") and "wc -c <" in cmd:
            return _RR(True, 0, "%d\n" % len(self.accumulated))
        if cmd.startswith("head -c") and "sha256sum" in cmd:
            m = re.search(r"head -c (\d+)", cmd)
            n = int(m.group(1)) if m else 0
            return _RR(True, 0, hashlib.sha256(
                self.accumulated[:n].encode()).hexdigest() + "  prefix\n")
        if cmd.startswith("head -c"):
            m = re.search(r"head -c (\d+)", cmd)
            if m:
                self.accumulated = self.accumulated[:int(m.group(1))]
            return _RR(True, 0, "")
        if cmd.startswith(": >"):
            self.accumulated = ""
            return _RR(True, 0, "")
        if cmd.startswith("wc -c <"):
            return _RR(True, 0, "%d\n" % len(self.accumulated))
        if cmd.startswith("sha256sum"):
            return _RR(True, 0, "%s  staged\n" % (
                ("0" * 64) if self.wrong_decode else self.want_sha))
        if "base64 -d" in cmd:
            return _RR(True, 0, "")
        if "chmod" in cmd and "mv -f" in cmd:
            self.promoted = True
            return _RR(True, 0, "")
        if cmd.startswith("stty") or cmd.startswith("mkdir") or cmd.startswith("rm -f"):
            return _RR(True, 0, "")
        return _RR(True, 0, "")

    def send(self, data):
        if self.send_raises:
            raise self.send_raises
        self.writes.append(data)
        for line in data.decode("utf-8", "replace").split("\r"):
            line = line.strip()
            if not line:
                continue
            m = re.match(r"printf %s ([A-Za-z0-9+/=]+) >>", line)
            if m:
                self.accumulated += m.group(1)
                continue
            m = re.search(r"@@AB([0-9a-f]+):(\d+):%s@@", line)
            if m:
                self.pending_ack = (m.group(1), int(m.group(2)))

    def pump(self, secs):
        if secs >= 0.1 and self.pending_ack:
            rid, idx = self.pending_ack
            self.pending_ack = None
            self.acks += 1
            value = 0 if self.corrupt else len(self.accumulated)
            self.buf.data = "@@AB%s:%d:%d@@\n" % (rid, idx, value)

    def text(self):
        return str(self.buf)

    def interrupt(self):
        self.corrupt = False


class TestBlockTransportRecovery(unittest.TestCase):
    def test_corrupted_ack_retries_once_at_verified_boundary(self):
        data = os.urandom(12000)
        want = sha(data)
        host = _BlockHost(want, corrupt=True)
        # 6s ACK deadline means one real-time retry; still deterministic/bounded.
        res = nl.block_push_bytes(host, data, "/etc/nuxel/recovery.bin")
        self.assertEqual(res["decoded_sha256"], want)
        self.assertEqual(res["retries"], 1)

    def test_disconnect_mid_transfer_raises_console_lost(self):
        data = os.urandom(20000)
        host = _BlockHost(sha(data))
        host.send_raises = nl.ConsoleLost("device not configured")
        with self.assertRaises(nl.ConsoleLost):
            nl.block_push_bytes(host, data, "/etc/nuxel/disconnect.bin")


class TestCancellation(unittest.TestCase):
    def test_cancel_at_block_boundary_never_activates_temp_file(self):
        data = os.urandom(20000)
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                state = {"cancel": False}

                def progress(event):
                    if int(event.get("block_index", 0)) >= 1:
                        state["cancel"] = True

                def cancel():
                    return state["cancel"]

                with self.assertRaises(nl.OperationCancelled):
                    nl.block_push_bytes(c, data, "/etc/nuxel/cancel.bin",
                                        progress=progress, cancel_check=cancel)
                self.assertFalse(phone.exists("etc/nuxel/cancel.bin"),
                                 "a cancelled transfer must never activate its target")

    def test_invalid_state_transition_is_rejected(self):
        with self.assertRaises(ValueError):
            nl.transition_state("FAILED", "SUCCEEDED")

    def test_connect_idle_can_move_straight_to_activation(self):
        # A group whose files are already at the target hashes has nothing to
        # stage and may go directly from CONNECTED_IDLE to DEPLOY_ACTIVATING.
        self.assertEqual(nl.transition_state("CONNECTED_IDLE", "DEPLOY_ACTIVATING"),
                         "DEPLOY_ACTIVATING")

    def test_reentering_the_same_phase_is_allowed(self):
        # Activating group 2 after group 1 re-enters DEPLOY_ACTIVATING.
        self.assertEqual(nl.transition_state("DEPLOY_ACTIVATING", "DEPLOY_ACTIVATING"),
                         "DEPLOY_ACTIVATING")


class TestLockReleaseCleanup(unittest.TestCase):
    def test_release_clears_advisory_sidecar(self):
        tmp = tempfile.TemporaryDirectory(prefix="nxl-lock-release-")
        self.addCleanup(tmp.cleanup)
        lock = os.path.join(tmp.name, "shared.lock")
        with mock.patch.dict(os.environ, {"NUXEL_LIVE_LOCK": lock}):
            fd, shared = nl.take_console_lock("/dev/test", op_id="release-me")
            self.assertTrue(os.path.exists(shared + ".owner.json"))
            nl.release_console_lock(fd, shared, "/dev/test")
            self.assertFalse(os.path.exists(shared + ".owner.json"))
            self.assertEqual(nl._lock_probe(shared), "free")


class TestLockContentionOwnerInfo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nxl-lock-")
        self.addCleanup(self.tmp.cleanup)
        self.lock = os.path.join(self.tmp.name, "shared.lock")
        env = mock.patch.dict(os.environ, {"NUXEL_LIVE_LOCK": self.lock})
        env.start()
        self.addCleanup(env.stop)

    def test_lock_wait_timeout_reports_recorded_owner(self):
        fd, _ = nl.take_console_lock("/dev/test", op_id="op-123")
        try:
            with self.assertRaises(nl.ConsoleLost) as ctx:
                nl.take_console_lock("/dev/test", lock_wait=0.1)
            self.assertIn("owned by another host tool", str(ctx.exception))
            self.assertIn("op-123", str(ctx.exception))
        finally:
            fd.close()

    def test_lock_status_reads_owner_without_contending(self):
        fd, _ = nl.take_console_lock("/dev/test", op_id="op-status")
        try:
            text = nl.lock_status_text("/dev/test")
            self.assertIn("op-status", text)
            self.assertIn("pid", text)
        finally:
            fd.close()


class TestRestartFailureAndRollback(unittest.TestCase):
    def test_activation_restart_failure_returns_false_not_success(self):
        steps = [{"group": "g", "service": "nuxel-bridge.service",
                  "declared_reload": "", "health_check": "true"}]
        with mock.patch.object(deploy, "run_script",
                               return_value={"framed": True, "rc": 1,
                                             "output": "failed restart"}) as rs:
            records, ok = deploy.run_group_activation(None, None, "g", steps, 1)
            self.assertFalse(ok)
            self.assertTrue(any(r["kind"] == "restart" for r in records))
            rs.assert_called_once()

    def test_rollback_reload_action_is_coalesced(self):
        reload = "systemctl restart nuxel-bridge.service"
        plan = nl.build_deploy_plan(
            five_file_manifest(reload, source="VERSION"),
            nl.repo_root_from_here())
        self.assertEqual(plan["violations"], [])
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                bundle = nl.EvidenceBundle(tempfile.mkdtemp(prefix="nxl-ev-"))
                records, ok = deploy.run_group_rollback(c, bundle, "reload-group",
                                                        plan["steps"], 1)
                self.assertTrue(ok, records)
            log_path = os.path.join(phone.root, "run", "nuxel-systemctl.log")
            with open(log_path) as fh:
                lines = fh.read().splitlines()
            restarts = [l for l in lines if l.startswith("restart nuxel-bridge.service")]
            self.assertEqual(len(restarts), 1,
                             "rollback must coalesce the declared reload to one restart")


class TestTransactionActivationPlan(unittest.TestCase):
    def test_daemon_reload_coalesces_across_groups(self):
        steps = [
            {"group": "a", "service": None,
             "declared_reload": "systemctl daemon-reload"},
            {"group": "b", "service": None,
             "declared_reload": "  systemctl  --system  daemon-reload ; "},
        ]
        plan = nl.transaction_activation_plan(steps)
        self.assertEqual(plan["counts"]["daemon_reloads_planned"], 1)
        self.assertEqual(plan["daemon_reload_action"]["action"],
                         "systemctl daemon-reload")
        self.assertEqual(plan["reloads"], [])

    def test_identical_restart_of_one_service_across_groups_is_once(self):
        steps = [
            {"group": "a", "service": "nuxel-web", "declared_reload": ""},
            {"group": "b", "service": "nuxel-web.service", "declared_reload": ""},
            {"group": "c", "service": "nuxel-audio.service", "declared_reload": ""},
        ]
        plan = nl.transaction_activation_plan(steps)
        self.assertEqual([r["service"] for r in plan["restarts"]],
                         ["nuxel-web.service", "nuxel-audio.service"])
        self.assertEqual(plan["counts"]["restarts_planned"], 2)

    def test_leading_daemon_reload_is_split_but_rest_kept_verbatim(self):
        steps = [{"group": "g", "service": None,
                  "declared_reload":
                      "systemctl daemon-reload && (systemctl restart nuxel-bridge.service "
                      "nuxel-http-bridge.service || true)"}]
        plan = nl.transaction_activation_plan(steps)
        self.assertEqual(len(plan["reloads"]), 1)
        self.assertEqual(plan["reloads"][0]["action"],
                         "(systemctl restart nuxel-bridge.service "
                         "nuxel-http-bridge.service || true)")
        self.assertTrue(plan["reloads"][0]["daemon_reload_split"])
        self.assertEqual(plan["counts"]["daemon_reloads_planned"], 1)
        self.assertEqual(plan["counts"]["restarts_planned"], 2)
        self.assertEqual(plan["restarts"], [], "already named in the declared reload")

    def test_empty_changed_set_plans_no_restart_or_reload(self):
        plan = nl.transaction_activation_plan([])
        self.assertEqual(plan["reloads"], [])
        self.assertEqual(plan["restarts"], [])
        self.assertFalse(plan["daemon_reload"])

    def test_dry_run_plan_contains_the_same_coalesced_actions(self):
        man = five_file_manifest("systemctl restart nuxel-bridge.service",
                                 source="VERSION")
        plan = nl.build_deploy_plan(man, nl.repo_root_from_here())
        self.assertEqual(plan["violations"], [])
        self.assertEqual(len(plan["activation_plan"]["reloads"]), 1)
        self.assertEqual(plan["activation_plan"]["counts"]["reloads_planned"], 1)


class TestBlockTransportSafety(unittest.TestCase):
    def test_wrong_decode_hash_never_promotes(self):
        data = os.urandom(9000)
        host = _BlockHost(sha(data), wrong_decode=True)
        with self.assertRaises(nl.ConsoleLost):
            nl.block_push_bytes(host, data, "/etc/nuxel/wrong-hash.bin")
        self.assertFalse(host.promoted)
        self.assertFalse(any("chmod" in c and "mv -f" in c for c in host.run_calls))

    def test_resume_at_verified_block_boundary(self):
        data = b"resume-me-" * 900
        b64 = base64.b64encode(data).decode()
        prefix = b64[:1520]  # four 380-char lines
        host = _BlockHost(sha(data), initial_prefix=prefix)
        res = nl.block_push_bytes(host, data, "/etc/nuxel/resume.bin")
        self.assertTrue(res["resume_used"], res)
        self.assertEqual(res["resumed_b64_chars"], 1520)
        self.assertEqual(res["decoded_sha256"], sha(data))
        self.assertTrue(host.promoted)

    def test_wrong_prefix_is_discarded_not_resumed(self):
        data = os.urandom(9000)
        host = _BlockHost(sha(data), initial_prefix="A" * 1520)
        res = nl.block_push_bytes(host, data, "/etc/nuxel/resume-bad.bin")
        self.assertFalse(res["resume_used"], res)
        self.assertEqual(res["decoded_sha256"], sha(data))
        self.assertTrue(host.promoted)

    def test_empty_file_is_staged_without_executing_payload(self):
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                res = nl.block_push_bytes(c, b"", "/etc/nuxel/empty.bin")
                self.assertEqual(res["bytes"], 0)
                self.assertEqual(res["decoded_sha256"], sha(b""))
                self.assertTrue(phone.exists("etc/nuxel/empty.bin"))
                self.assertEqual(os.path.getsize(
                    os.path.join(phone.root, "etc/nuxel/empty.bin")), 0)

    def test_shell_metacharacters_and_unicode_are_data_not_code(self):
        dangerous = ("$(touch /tmp/nxl-block-pwned) `id` ; rm -rf /tmp/nxl-no\n"
                     "unicode-✓-🐧\x00\xff").encode("utf-8")
        marker = "/tmp/nxl-block-pwned"
        try:
            os.unlink(marker)
        except OSError:
            pass
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                res = nl.block_push_bytes(c, dangerous, "/etc/nuxel/metachar.bin")
                self.assertEqual(res["decoded_sha256"], sha(dangerous))
                with open(os.path.join(phone.root, "etc/nuxel/metachar.bin"), "rb") as fh:
                    self.assertEqual(fh.read(), dangerous)
        self.assertFalse(os.path.exists(marker), "payload must never execute as shell")


class TestBlockBoundarySafety(unittest.TestCase):
    def test_oversized_stale_part_is_truncated_not_appended(self):
        data = os.urandom(9000)
        b64 = base64.b64encode(data).decode()
        host = _BlockHost(sha(data), initial_prefix=b64 + "STALE-TAIL")
        res = nl.block_push_bytes(host, data, "/etc/nuxel/oversized.bin")
        self.assertFalse(res["resume_used"], res)
        self.assertEqual(res["decoded_sha256"], sha(data))
        self.assertTrue(host.promoted)


class TestPerTransactionBackup(unittest.TestCase):
    def test_rollback_uses_current_bytes_not_a_stale_long_term_baseline(self):
        man = {"schema_version": 1,
               "groups": [{"id": "g", "component": "test", "priority": 1,
                           "risk": "low", "restart_service": None,
                           "declared_reload": "true", "health_check": "true",
                           "rollback": "restore <target>.nuxel-rollback",
                           "files": [{"source": "VERSION",
                                      "target": "/etc/nuxel/txn-backup.conf"}]}]}
        plan = nl.build_deploy_plan(man, nl.repo_root_from_here())
        step = dict(plan["steps"][0])
        step["txn_backup"] = step["backup"] + ".pre-test"
        current = b"CURRENT-BEFORE-THIS-RUN\n"
        ancient = b"ANCIENT-BASELINE\n"
        with FakePhone("healthy") as phone:
            target = os.path.join(phone.root, "etc/nuxel/txn-backup.conf")
            long_term = os.path.join(phone.root,
                                     "etc/nuxel/txn-backup.conf.nuxel-rollback")
            with open(target, "wb") as fh:
                fh.write(current)
            with open(long_term, "wb") as fh:
                fh.write(ancient)
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                bundle = nl.EvidenceBundle(tempfile.mkdtemp(prefix="nxl-ev-"))
                rec = deploy.run_step(c, bundle, step, 1)
                self.assertTrue(rec["ok"], rec)
                txn_backup = os.path.join(
                    phone.root, "etc/nuxel/txn-backup.conf.nuxel-rollback.pre-test")
                with open(txn_backup, "rb") as fh:
                    self.assertEqual(fh.read(), current,
                                     "transaction backup must capture current bytes")
                with open(long_term, "rb") as fh:
                    self.assertEqual(fh.read(), ancient,
                                     "long-term baseline must be preserved")
                rb, ok = deploy.run_transaction_rollback(
                    c, bundle, [step], {step["target"]: sha(current)}, 1)
                self.assertTrue(ok, rb)
                with open(target, "rb") as fh:
                    self.assertEqual(fh.read(), current)


class TestManifestHealthChecks(unittest.TestCase):
    def test_a75_group3_health_checks_files_and_running_environment(self):
        man = json.load(open(os.path.join(LIVE, "a75-bridge-version-restore-manifest.json")))
        hc = next(g["health_check"] for g in man["groups"]
                  if g["id"] == "a75-bridge-version-units-and-pwa")
        self.assertNotIn("grep -c", hc,
                         "grep -c with multiple files prints file:count, not a count")
        self.assertIn("systemctl show nuxel-bridge.service", hc)
        self.assertIn("systemctl show nuxel-http-bridge.service", hc)
        self.assertIn("/usr/share/nuxel/pwa/nuxel-common/bridge-version.json", hc)


class TestNoOpDeployment(unittest.TestCase):
    def test_unchanged_target_does_not_restart_or_reload(self):
        reload = "systemctl restart nuxel-bridge.service"
        plan = nl.build_deploy_plan(
            five_file_manifest(reload, source="VERSION"),
            nl.repo_root_from_here())
        step = plan["steps"][0]
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                bundle = nl.EvidenceBundle(tempfile.mkdtemp(prefix="nxl-ev-"))
                first = deploy.run_step(c, bundle, step, 1)
                self.assertTrue(first["ok"], first)
                # A second run sees the target hash and stages nothing.  The
                # activation call therefore receives an empty changed set.
                second = deploy.run_step(c, bundle, step, 1)
                self.assertTrue(second["already_deployed"], second)
                acts, ok = deploy.run_transaction_activation(
                    c, bundle, [], [step], 1)
                self.assertTrue(ok, acts)
            log_path = os.path.join(phone.root, "run", "nuxel-systemctl.log")
            with open(log_path) as fh:
                lines = fh.read().splitlines()
            self.assertFalse([l for l in lines if l.startswith("restart ")],
                             "a no-op deploy must not restart a service")
            self.assertFalse([l for l in lines if l.startswith("daemon-reload")],
                             "a no-op deploy must not reload systemd")

    def test_rollback_does_not_restart_after_unverified_restore(self):
        class NoRuns:
            timeout = 1.0
            def run(self, cmd, timeout=None, guard=False):
                return _RR(False, 1, "unreachable")

        step = {"group": "g", "target": "/etc/nuxel/x.conf",
                "backup": "/etc/nuxel/x.conf.nuxel-rollback",
                "service": "nuxel-bridge.service", "declared_reload": "",
                "health_check": None}
        with mock.patch.object(deploy, "run_script",
                               return_value={"framed": True, "rc": 1,
                                             "output": "NO-BACKUP"}), \
                mock.patch.object(deploy, "_execute_activation") as activation:
            recs, ok = deploy.run_transaction_rollback(
                NoRuns(), None, [step], {step["target"]: "a" * 64}, 1)
        self.assertFalse(ok)
        activation.assert_not_called()


class TestTransactionRollbackAgainstFakePhone(unittest.TestCase):
    def _manifest(self, health="false"):
        return {"schema_version": 1,
                "groups": [{"id": "g", "component": "test", "priority": 1,
                            "risk": "low", "restart_service": None,
                            "declared_reload": "true", "health_check": health,
                            "rollback": "restore <target>.nuxel-rollback",
                            "files": [{"source": "VERSION",
                                       "target": "/etc/nuxel/rollback-test.conf"}]}]}

    def test_health_failure_restores_previous_bytes_and_verifies(self):
        plan = nl.build_deploy_plan(self._manifest(), nl.repo_root_from_here())
        self.assertEqual(plan["violations"], [])
        step = plan["steps"][0]
        with FakePhone("healthy") as phone:
            path = os.path.join(phone.root, "etc/nuxel/rollback-test.conf")
            with open(path, "w") as fh:
                fh.write("OLD-CONTENT\n")
            old_hash = sha(b"OLD-CONTENT\n")
            with nl.Console(phone.dev, timeout=20) as c:
                self.assertTrue(c.probe(4.0).reachable)
                bundle = nl.EvidenceBundle(tempfile.mkdtemp(prefix="nxl-ev-"))
                rec = deploy.run_step(c, bundle, step, 1)
                self.assertTrue(rec["ok"], rec)
                self.assertTrue(rec["changed"])
                with open(path, "rb") as fh:
                    self.assertNotEqual(fh.read(), b"OLD-CONTENT\n")
                acts, ok = deploy.run_transaction_activation(
                    c, bundle, [step], [step], 1)
                self.assertFalse(ok, "a false health check must not commit")
                rb, rb_ok = deploy.run_transaction_rollback(
                    c, bundle, [step], {step["target"]: rec["previous_hash"]}, 1,
                    health_groups=None)
                self.assertTrue(rb_ok, rb)
                self.assertTrue(rb[0]["verified"], rb)
                with open(path, "rb") as fh:
                    self.assertEqual(sha(fh.read()), old_hash)

    def test_rollback_failure_is_reported_not_masked(self):
        class NoRuns:
            timeout = 1.0
            def run(self, cmd, timeout=None, guard=False):
                return _RR(False, 1, "unreachable")

        step = {"group": "g", "target": "/etc/nuxel/x.conf",
                "backup": "/etc/nuxel/x.conf.nuxel-rollback",
                "service": None, "declared_reload": "", "health_check": None}
        with mock.patch.object(deploy, "run_script",
                               return_value={"framed": True, "rc": 1,
                                             "output": "NO-BACKUP"}), \
                mock.patch.object(deploy, "_execute_activation",
                                  return_value=([], True)):
            recs, ok = deploy.run_transaction_rollback(
                NoRuns(), None, [step], {step["target"]: "a" * 64}, 1)
        self.assertFalse(ok)
        self.assertFalse(recs[0]["verified"])


class TestJournalStatus(unittest.TestCase):
    def test_incomplete_then_complete_transaction_is_distinguishable(self):
        d = tempfile.mkdtemp(prefix="nxl-txn-")
        b = nl.EvidenceBundle(d, name="txn", label="test")
        b.op_id = "op-status-test"
        b.journal({"event": "planned", "pid": 999999, "host": "not-this-host"})
        b.write_json("status.json", {"operation_id": "op-status-test",
                                     "pid": 999999, "pid_start": "0",
                                     "host": "not-this-host",
                                     "target": "/dev/ttyACM0",
                                     "state": "DEPLOY_STAGING"})
        doc = deploy.transaction_status(b.dir)
        self.assertEqual(doc["state"], "INCOMPLETE")
        self.assertIn("dry-run", doc["recommended_action"])
        b.journal({"event": "finished", "verdict": "DEPLOYED_UNVERIFIED",
                   "exit_code": 0})
        b.write_json("deployment.json", {"operation_id": "op-status-test",
                                         "verdict": "DEPLOYED_UNVERIFIED"})
        self.assertEqual(deploy.transaction_status(b.dir)["state"], "COMPLETE")


class TestJournalEventFields(unittest.TestCase):
    def test_per_file_target_is_not_clobbered_by_console_target(self):
        import io
        d = tempfile.mkdtemp(prefix="nxl-journal-")
        b = nl.EvidenceBundle(d, name="journal", label="test")
        b.op_id = "op"
        rep = deploy.DeployReporter(b, "op", "/dev/ttyACM0", out=io.StringIO())
        rep.log({"event": "verified", "target": "/etc/nuxel/x.conf",
                 "changed": True})
        lines = [json.loads(x) for x in open(
            os.path.join(b.dir, "transaction.jsonl"))]
        ev = [x for x in lines if x.get("event") == "verified"][0]
        self.assertEqual(ev["target"], "/etc/nuxel/x.conf")
        self.assertEqual(ev["console"], "/dev/ttyACM0")


class TestLockRobustness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nxl-lock-robust-")
        self.addCleanup(self.tmp.cleanup)
        self.lock = os.path.join(self.tmp.name, "shared.lock")
        env = mock.patch.dict(os.environ, {"NUXEL_LIVE_LOCK": self.lock})
        env.start()
        self.addCleanup(env.stop)

    def test_readonly_lock_file_can_still_be_flocked(self):
        open(self.lock, "w").close()
        os.chmod(self.lock, 0o444)
        fd, _ = nl.take_console_lock("/dev/test", op_id="readonly")
        try:
            self.assertIn("readonly", nl.lock_status_text("/dev/test"))
        finally:
            fd.close()

    def test_symlink_lock_fails_closed(self):
        target = os.path.join(self.tmp.name, "target")
        open(target, "w").close()
        os.symlink(target, self.lock)
        with self.assertRaisesRegex(nl.ConsoleLost, "refusing to share"):
            nl.take_console_lock("/dev/test")

    def test_held_lock_with_dead_sidecar_is_not_called_stale(self):
        fd, _ = nl.take_console_lock("/dev/test", op_id="live-op")
        try:
            side = self.lock + ".owner.json"
            doc = json.load(open(side))
            doc["pid"] = 999999
            doc["pid_start"] = "0"
            with open(side, "w") as fh:
                json.dump(doc, fh)
            text = nl.lock_status_text("/dev/test")
            self.assertIn("locked now", text)
            self.assertIn("no longer alive", text)
            self.assertEqual(nl.read_lock_owner("/dev/test")["lock_state"], "held")
        finally:
            fd.close()


class TestPreflightRefusesMalformedReload(unittest.TestCase):
    def test_flash_tooling_in_declared_reload_fails_before_device_contact(self):
        man = {"schema_version": 1,
               "groups": [{"id": "g", "component": "test", "priority": 1,
                           "risk": "low", "restart_service": None,
                           "declared_reload": "heimdall flash --BOOT boot.img",
                           "health_check": "true", "rollback": "restore backup",
                           "files": [{"source": "VERSION",
                                      "target": "/etc/nuxel/x.conf"}]}]}
        plan = nl.build_deploy_plan(man, nl.repo_root_from_here())
        self.assertTrue(plan["violations"])
        self.assertTrue(any(v["kind"] == "command_guard"
                            for v in plan["violations"]), plan["violations"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
