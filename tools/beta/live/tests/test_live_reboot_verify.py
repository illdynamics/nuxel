#!/usr/bin/env python3
"""Offline tests for tools/beta/live/nuxel-live-reboot-verify.py (briq-10c).

Run:  python3 tools/beta/live/tests/test_live_reboot_verify.py

These tests NEVER touch the phone.  They drive the briq-10c state machine against
the offline fake console (tests/fake_console.py), which now models a power cycle:
`systemctl reboot` ends the session, the PTY disappears, a *new* PTY appears with
a different kernel boot_id, a reset uptime and an incremented boot counter.

What is proven here:
  * the probe rules refuse to promote anything the device did not actually say
    (a writable mixer is NEEDS_OWNER_TEST, a silent IRQ line is BLOCKED_KERNEL,
    a missing card is BLOCKED_FIRMWARE, a missing registry is FAILED, …);
  * the real-reboot proof needs an independent signal (boot_id / uptime /
    boot counter) and says so honestly when nothing changed;
  * the reboot policy refuses a blind reboot (no reason/diagnostic, repeat
    diagnostic, exhausted budget) before any command is sent;
  * a silent console terminates BLOCKED_EXTERNAL_RESOURCE without writing;
  * the full cycle — pre-checklist, policy, reboot, reconnect watch, real-reboot
    proof, post checklist, probe set, evidence bundle + SHA-256 manifest and the
    persisted reboot history — runs end to end and is stamped OFFLINE_TESTED.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.abspath(os.path.join(HERE, ".."))
TOOL = os.path.join(LIVE, "nuxel-live-reboot-verify.py")

sys.path.insert(0, HERE)
sys.path.insert(0, LIVE)
from harness import FakePhone, load_live  # noqa: E402

nl = load_live()
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("nuxel_live_reboot_verify", TOOL)
rv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rv)


def run_tool(extra, timeout=240):
    """Run the real CLI in a subprocess and return (rc, report-dict, stdout)."""
    with tempfile.TemporaryDirectory(prefix="nxl-rv-ev-") as ev:
        cmd = [sys.executable, TOOL, "--evidence-dir", ev, "--json"] + extra
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        report = {}
        try:
            report = json.loads(p.stdout[p.stdout.index("{"):])
        except (ValueError, IndexError):
            pass
        return p.returncode, report, p.stdout + p.stderr, ev


class TestProbeRules(unittest.TestCase):
    """Every rule may only read what the device returned."""

    def _v(self, rule_id, out, rc=0):
        verdict, reason = rv.PROBE_RULES[rule_id][1](out, rc)
        self.assertIn(verdict, nl.VALID_VERDICTS,
                      "rule %s produced %r outside the mission vocabulary" % (rule_id, verdict))
        self.assertTrue(reason)
        return verdict

    def test_touch_gate_pass_is_the_only_promotion(self):
        self.assertEqual(self._v("touch-pipeline", "CAPTURE_GATE=PASS events=42"), "VERIFIED_ON_S10PLUS")
        self.assertEqual(self._v("touch-pipeline", "boot classified: charger-mode lpcharge"),
                         "BLOCKED_KERNEL")
        self.assertEqual(self._v("touch-pipeline", "CAPTURE_GATE=BLOCKED no node"), "BLOCKED_HARDWARE")
        self.assertEqual(self._v("touch-pipeline", "CAPTURE_GATE=FAIL no finger"), "NEEDS_OWNER_TEST")

    def test_audio_walk_never_claims_sound(self):
        self.assertEqual(self._v("audio-abox", '{"first_broken_stage": "dapm route"}'), "FAILED")
        self.assertEqual(self._v("audio-abox", "card beyond-madera pcm ok dapm ok dac ok"),
                         "NEEDS_OWNER_TEST")
        self.assertEqual(self._v("audio-abox", "aplay: no soundcards found"), "BLOCKED_FIRMWARE")

    def test_fb_owner_requires_a_single_owner(self):
        self.assertEqual(self._v("fb-owner", "nuxel-wl-fb\nowner=nuxel-wl-fb pid=812"),
                         "VERIFIED_ON_S10PLUS")
        self.assertEqual(self._v("fb-owner", "nuxel-ui\n"), "FAILED")

    def test_irq_counter_distinguishes_mapped_from_delivered(self):
        self.assertEqual(self._v("sec-ts-irq", " 41:      92833          0   GIC  41 Level  sec_ts"),
                         "DEPLOYED_UNVERIFIED")
        self.assertEqual(self._v("sec-ts-irq", " 41:          0          0   GIC  41 Level  sec_ts"),
                         "BLOCKED_HARDWARE")
        self.assertEqual(self._v("sec-ts-irq", ""), "BLOCKED_KERNEL")

    def test_registry_and_charger_mode(self):
        self.assertEqual(self._v("pwa-registry", '{"schema":1,"apps":[]}'), "VERIFIED_ON_S10PLUS")
        self.assertEqual(self._v("pwa-registry", "curl: (7) Failed to connect"), "FAILED")
        self.assertEqual(self._v("charger-mode", "lpcharge: entered"), "BLOCKED_KERNEL")
        self.assertEqual(self._v("charger-mode", "1\n"), "DEPLOYED_UNVERIFIED")


class TestRebootProof(unittest.TestCase):
    def test_boot_id_change_proves_the_reboot(self):
        pre = {"boot_id": "aaa", "uptime": "18432.55 51233.11", "boot_count": "7"}
        post = {"boot_id": "bbb", "uptime": "24.10 91.44", "boot_count": "8"}
        proof = rv.reboot_proof(pre, post)
        self.assertTrue(proof["rebooted"])
        self.assertTrue(proof["boot_id_changed"])
        self.assertTrue(proof["uptime_went_backwards"])
        self.assertTrue(proof["boot_count_increased"])
        self.assertEqual(len(proof["signals"]), 3)

    def test_unchanged_device_is_not_a_reboot(self):
        pre = {"boot_id": "aaa", "uptime": "100.0 200.0", "boot_count": "7"}
        post = {"boot_id": "aaa", "uptime": "140.0 240.0", "boot_count": "7"}
        proof = rv.reboot_proof(pre, post)
        self.assertFalse(proof["rebooted"])
        self.assertIn("NOT counted", proof["note"])

    def test_missing_boot_counter_is_tolerated(self):
        pre = {"boot_id": "x", "uptime": "10 20", "boot_count": "cat: No such file"}
        post = {"boot_id": "y", "uptime": "3 9", "boot_count": "cat: No such file"}
        proof = rv.reboot_proof(pre, post)
        self.assertTrue(proof["rebooted"])
        self.assertNotIn("boot_count_increased", proof)


class TestPolicyRefusals(unittest.TestCase):
    def test_reboot_without_reason_is_deferred_and_sends_nothing(self):
        with FakePhone("healthy") as phone:
            devfile = os.path.join(phone.workdir, "dev")
            with open(devfile, "w") as fh:
                fh.write(phone.dev + "\n")
            rc, report, out, ev = run_tool(["--dev-file", devfile, "--reboot",
                                            "--probe-set", "none", "--simulated",
                                            "--probe-seconds", "1.5", "--timeout", "10"])
            self.assertEqual(rc, 4, out)
            self.assertEqual(report["verdict"], "DEFERRED")
            self.assertFalse(os.path.exists(os.path.join(phone.root, "run",
                                                         "reboot-requested")))

    def test_silent_console_is_blocked_external_resource(self):
        with FakePhone("silent") as phone:
            devfile = os.path.join(phone.workdir, "dev")
            with open(devfile, "w") as fh:
                fh.write(phone.dev + "\n")
            rc, report, out, ev = run_tool(["--dev-file", devfile, "--probe-set", "none",
                                            "--simulated", "--probe-seconds", "1.5",
                                            "--timeout", "6"])
            self.assertEqual(rc, 3, out)
            self.assertEqual(report["verdict"], "BLOCKED_EXTERNAL_RESOURCE")
            self.assertIn("byte-silent", report["blocked_reason"])

    def test_exhausted_budget_refuses_the_reboot(self):
        with FakePhone("healthy") as phone:
            devfile = os.path.join(phone.workdir, "dev")
            with open(devfile, "w") as fh:
                fh.write(phone.dev + "\n")
            hist = os.path.join(phone.workdir, "reboots.json")
            with open(hist, "w") as fh:
                json.dump([{"n": 1, "reason": "r", "diagnostic": "d",
                            "returned_to_nuxel": True}], fh)
            rc, report, out, ev = run_tool(["--dev-file", devfile, "--reboot",
                                            "--reason", "apply staged userspace",
                                            "--diagnostic", "post-boot probe",
                                            "--max-reboots", "1", "--history", hist,
                                            "--probe-set", "none", "--simulated",
                                            "--probe-seconds", "1.5", "--timeout", "10"])
            self.assertEqual(rc, 4, out)
            self.assertEqual(report["verdict"], "DEFERRED")
            self.assertIn("budget", report["reboot"]["reason"])


class TestProbeStaging(unittest.TestCase):
    def test_missing_diagnostic_is_pushed_through_verified_frames(self):
        with FakePhone("healthy") as phone:
            with nl.Console(phone.dev, timeout=20) as c:
                staged = []
                for rel in ("tools/s10plus/a33/nuxel-touch-capture.sh",):
                    with open(os.path.join(nl.repo_root_from_here(), rel), "rb") as fh:
                        data = fh.read()
                    target = os.path.join(rv.PROBE_DIR, os.path.basename(rel))
                    info = nl.push_bytes(c, data, target, mode="0755")
                    staged.append((rel, target, info))
                rel, target, info = staged[0]
                self.assertGreater(info["frames"], 0)
                self.assertTrue(phone.exists(target), "pushed script must exist on device")
                res = c.run("test -x %s && echo EXEC || echo NOEXEC" % target)
                self.assertTrue(res.ok)
                self.assertIn("EXEC", res.output)


class TestEndToEndRebootCycle(unittest.TestCase):
    def test_full_cycle_offline(self):
        with FakePhone("healthy") as phone:
            devfile = os.path.join(phone.workdir, "console-dev")
            with open(devfile, "w") as fh:
                fh.write(phone.dev + "\n")
            # the "device" power-cycles: a fresh console appears on a NEW pty
            t = threading.Thread(target=phone.restart_after_reboot,
                                 args=(devfile,), kwargs={"mode": "post-reboot",
                                                          "timeout": 60},
                                 daemon=True)
            rc, report, out, ev = run_tool([
                "--dev-file", devfile, "--reboot",
                "--reason", "apply the staged userspace deploy and prove return-to-Nuxel",
                "--diagnostic", "post-boot fb-owner + registry + sec_ts IRQ probe",
                "--probe-set", "live",
                "--probes", "fb-owner,pwa-registry,sec-ts-irq,charger-mode",
                "--simulated", "--reconnect-timeout", "90", "--poll-interval", "0.4",
                "--probe-seconds", "1.5", "--timeout", "10", "--max-reboots", "1"],
                timeout=300)
            t.join(timeout=60)
            self.assertEqual(rc, 0, out)
            self.assertTrue(report["simulated"])
            self.assertEqual(report["verdict"], "OFFLINE_TESTED",
                            "a simulated cycle may never claim VERIFIED_ON_S10PLUS")
            self.assertTrue(report["reboot"]["returned_to_nuxel"])
            self.assertTrue(report["reboot"]["proof"]["rebooted"])
            self.assertTrue(report["reboot"]["proof"]["boot_id_changed"])
            # post-reboot checklist must be green on the healthy fake tree
            self.assertEqual([i["id"] for i in report["checklists"]["post"]
                              if i["status"] != "pass"], [])
            # every probe produced a verdict from the vocabulary
            self.assertEqual(len(report["probes"]), 4)
            for p in report["probes"]:
                self.assertIn(p["verdict"], nl.VALID_VERDICTS)
            # the reboot history persisted, so a blind repeat is impossible
            hist = json.load(open(os.path.join(ev, "reboots.json")))
            self.assertEqual(len(hist), 1)
            self.assertTrue(hist[0]["returned_to_nuxel"])
            # evidence bundle + SHA-256 manifest
            bundles = [d for d in os.listdir(ev) if d.startswith("reboot-verify-sim")]
            self.assertEqual(len(bundles), 1)
            sums = os.path.join(ev, bundles[0], "SHA256SUMS")
            self.assertTrue(os.path.exists(sums))
            self.assertGreater(len(open(sums).read().strip().splitlines()), 5)

    def test_second_identical_reboot_is_refused_by_history(self):
        """The persisted history must stop a blind repeat in a *later* run."""
        with FakePhone("healthy") as phone:
            devfile = os.path.join(phone.workdir, "console-dev")
            with open(devfile, "w") as fh:
                fh.write(phone.dev + "\n")
            hist = os.path.join(phone.workdir, "reboots.json")
            with open(hist, "w") as fh:
                json.dump([{"n": 1, "reason": "same reason",
                            "diagnostic": "same diagnostic", "returned_to_nuxel": True}], fh)
            rc, report, out, ev = run_tool([
                "--dev-file", devfile, "--reboot", "--reason", "same reason",
                "--diagnostic", "same diagnostic", "--history", hist,
                "--probe-set", "none", "--simulated", "--probe-seconds", "1.5",
                "--timeout", "10"])
            self.assertEqual(rc, 4, out)
            self.assertEqual(report["verdict"], "DEFERRED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
