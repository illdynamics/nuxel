#!/usr/bin/env python3
"""Offline tests for the Nuxel permission manager (briq-05a).

Run: python3 shell/nuxel-shell/nuxel-permissions/tests/test-permissions.py
(no third-party dependencies; works on macOS and on Fedora, so the checks run
in the repository CI as well as on the device).

What is asserted here is the *truth discipline*, not just plumbing:
unsupported capabilities can never be granted, a stored grant always carries
its limitation + attacker class, a kernel without Landlock downgrades the
claim instead of hiding it, and sandbox profiles never widen beyond the app
registry.
"""

import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PERM_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(PERM_DIR)))
PERMD = os.path.join(PERM_DIR, "nuxel-permd.py")
VERIFY = os.path.join(REPO, "tools", "s10plus", "a33", "verify-permissions.py")
FIXTURE = os.path.join(REPO, "tools", "s10plus", "a33", "security-fixtures",
                       "s10plus-4.14.253.json")

sys.path.insert(0, PERM_DIR)
import importlib.util

spec = importlib.util.spec_from_file_location("nuxel_permd", PERMD)
permd = importlib.util.module_from_spec(spec)
sys.modules["nuxel_permd"] = permd
spec.loader.exec_module(permd)


class TempStoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nuxel-perm-test-")
        self.store = permd.Store(self.tmp)
        self.registry = self.store.registry

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.tmp)


class TestRegistry(TempStoreCase):
    def test_alias_resolution(self):
        for token, expected in (("camera:capture", "camera"),
                                ("mic", "microphone"),
                                ("audio:capture", "microphone"),
                                ("storage:cache", "storage"),
                                ("location:read", "location"),
                                ("notifications:send", "notifications")):
            cap_id, why = self.registry.resolve(token)
            self.assertEqual(cap_id, expected, "%s -> %s (%s)" % (token, cap_id, why))

    def test_phone_status_is_not_call(self):
        # A namespace token must never be widened into the namespace's alias.
        cap_id, _ = self.registry.resolve("phone:status")
        self.assertEqual(cap_id, "phone_status")
        cap_id, ok = self.registry.resolve("phone")
        self.assertEqual(cap_id, "call")

    def test_refused_tokens(self):
        for token in ("sms_send_raw", "modem:raw", "landlock", "ptrace", "root", "sudo"):
            cap_id, why = self.registry.resolve(token)
            self.assertIsNone(cap_id, token)
            self.assertTrue(why.startswith("unsupported"), why)

    def test_unknown_token_is_none_not_guessed(self):
        cap_id, why = self.registry.resolve("webview:external")
        self.assertIsNone(cap_id)
        self.assertTrue(why.startswith("unknown"), why)

    def test_no_capability_claims_full_enforcement_without_a_kernel_mechanism(self):
        for row in self.registry.matrix():
            if row["enforceable"] == "yes":
                self.assertTrue(row["mechanisms"], row)
                self.assertNotIn("none", row["mechanisms"], row)
            self.assertIn(row["enforces_against"],
                          ("unprivileged-app", "some-apps", "nobody"), row)
            self.assertTrue(row["limitation"], row["id"])
            self.assertTrue(row["verdict"], row["id"])


class TestStore(TempStoreCase):
    def test_grant_is_portal_compatible_and_carries_truth(self):
        rec = self.store.grant("nuxel-dialer", "network")
        self.assertEqual(rec["duration"], "always")
        with open(self.store.grants_path("nuxel-dialer")) as fh:
            raw = json.load(fh)
        self.assertIn("network", raw)
        entry = raw["network"]
        # portal.py:PermissionStore reads exactly these keys
        for key in ("granted_at", "duration", "portal_type"):
            self.assertIn(key, entry)
        # ... and the reviewable truth is stored beside them
        for key in ("mechanisms", "enforceable", "enforces_against", "limitation"):
            self.assertIn(key, entry)
        self.assertNotEqual(entry["enforceable"], "yes",
                            "network must not claim full kernel enforcement on 4.14")

    def test_unsupported_capability_is_refused(self):
        with self.assertRaises(permd.UnsupportedCapability):
            self.store.grant("nuxel-dialer", "sms_send_raw")
        self.assertEqual(self.store.get_grants("nuxel-dialer"), {})

    def test_unknown_capability_is_refused(self):
        with self.assertRaises(permd.UnsupportedCapability):
            self.store.grant("nuxel-dialer", "definitely-not-a-capability")

    def test_revoke_and_revoke_all(self):
        self.store.grant("nuxel-messages", "sms")
        self.store.grant("nuxel-messages", "contacts")
        self.assertTrue(self.store.is_granted("nuxel-messages", "sms"))
        self.store.revoke("nuxel-messages", "sms")
        self.assertFalse(self.store.is_granted("nuxel-messages", "sms"))
        self.store.grant("nuxel-messages", "sms")
        revoked = self.store.revoke_all("nuxel-messages")
        self.assertEqual(sorted(revoked), ["contacts", "sms"])
        self.assertEqual(self.store.get_grants("nuxel-messages"), {})

    def test_once_grant_is_consumed(self):
        self.store.grant("camera-gallery", "camera", duration="once")
        self.assertTrue(self.store.is_granted("camera-gallery", "camera",
                                              consume_once=True))
        self.assertFalse(self.store.is_granted("camera-gallery", "camera"))
        with open(self.store.audit_path()) as fh:
            self.assertIn("once-consumed", fh.read())

    def test_invalid_duration_rejected(self):
        with self.assertRaises(ValueError):
            self.store.grant("nuxel-dialer", "network", duration="forever")

    def test_state_records_enforcement_snapshot(self):
        self.store.grant("camera-gallery", "camera")
        state = self.store.get_state("camera-gallery")
        self.assertEqual(state["grants"]["camera"]["enforceable"], "partial")
        self.assertEqual(state["enforcement"]["camera"]["enforces_against"],
                         "unprivileged-app")

    def test_audit_trail_is_append_only_jsonl(self):
        self.store.grant("nuxel-dialer", "network")
        self.store.revoke("nuxel-dialer", "network")
        with open(self.store.audit_path()) as fh:
            lines = [json.loads(line) for line in fh.read().splitlines() if line.strip()]
        self.assertEqual([l["action"] for l in lines], ["grant", "revoke"])
        for line in lines:
            self.assertIn("ts", line)
            self.assertIn("actor", line)


class TestKernelTruth(TempStoreCase):
    def test_4_14_fixture_downgrades_landlock(self):
        facts = permd.kernel_facts(FIXTURE)
        self.assertEqual(facts["release"], "4.14.253")
        self.assertEqual(facts["features"]["landlock"]["available"], "no")
        self.assertEqual(facts["features"]["nft_socket_cgroupv2"]["available"], "no")
        self.assertEqual(facts["mechanism_availability"]["landlock"], "no")
        self.assertEqual(facts["mechanism_availability"]["seccomp_bpf"], "yes")
        self.assertEqual(facts["mechanism_availability"]["cgroup_v2"], "yes")

    def test_capability_claims_are_capped_by_the_kernel(self):
        facts = permd.kernel_facts(FIXTURE)
        row = permd.downgrade_for_kernel(self.registry.enforcement_of("camera"), facts)
        self.assertTrue(row["kernel_missing"])
        self.assertTrue(any("Landlock" in m for m in row["kernel_missing"]))

    def test_unknown_stays_unknown(self):
        facts = permd.kernel_facts(FIXTURE)
        # no LSM list in the fixture -> apparmor must NOT be reported as absent
        self.assertEqual(facts["apparmor_enabled"], "unknown")


class TestEnforcePlan(TempStoreCase):
    def test_network_grant_opens_the_app_cgroup_only(self):
        self.store.grant("nuxel-dialer", "network")
        plan = permd.enforce_plan(REPO, self.store, self.registry, "nuxel-dialer")
        self.assertEqual(plan["sandbox"]["network_class"], "public")
        self.assertEqual(plan["sandbox"]["nft_match"],
                         "meta cgroup 0x%08x" % plan["sandbox"]["cgroup_classid"])
        # the app registry's classid is authoritative when present
        self.assertEqual(plan["sandbox"]["cgroup_classid"], 16973825)

    def test_no_grant_means_isolated_and_no_devices(self):
        plan = permd.enforce_plan(REPO, self.store, self.registry, "nuxel-messages")
        self.assertEqual(plan["sandbox"]["network_class"], "isolated")
        self.assertEqual(plan["sandbox"]["advisory_devices"], [])

    def test_plan_always_documents_the_kernel_gap(self):
        facts = permd.kernel_facts(FIXTURE)
        self.store.grant("camera-gallery", "camera")
        plan = permd.enforce_plan(REPO, self.store, self.registry, "camera-gallery",
                                  facts=facts)
        joined = " ".join(plan["honest_notes"])
        self.assertIn("landlock_unavailable", joined)
        self.assertIn("nft_cgroupv2_unavailable", joined)


class TestRepositoryDeclarations(unittest.TestCase):
    """The repository itself must stay internally consistent."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nuxel-perm-repo-")
        self.registry = permd.Registry()

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.tmp)

    def test_every_sandbox_profile_is_valid_and_resolvable(self):
        profiles = glob.glob(os.path.join(REPO, "shell/nuxel-shell/nuxel-sandbox",
                                          "profiles", "*.json"))
        self.assertGreaterEqual(len(profiles), 8)
        for path in profiles:
            with open(path) as fh:
                data = json.load(fh)
            for token in data.get("capabilities", []) or []:
                cap_id, why = self.registry.resolve(token)
                self.assertIsNotNone(cap_id, "%s: %s (%s)" % (path, token, why))

    def test_sandbox_profiles_never_widen_beyond_the_app_registry(self):
        reg_path = os.path.join(REPO, "configs/nuxel/app-registry/app_registry.json")
        with open(reg_path) as fh:
            registry = json.load(fh)
        declared = {}
        for app in registry["apps"]:
            caps = set()
            for token in app.get("capabilities", []) or []:
                cap_id, _ = self.registry.resolve(token)
                caps.add(cap_id or token)
            declared[app["app_id"]] = caps
        for path in glob.glob(os.path.join(REPO, "shell/nuxel-shell/nuxel-sandbox",
                                          "profiles", "*.json")):
            with open(path) as fh:
                data = json.load(fh)
            if data.get("template"):
                continue
            app_id = data.get("app_id")
            if app_id not in declared:
                continue
            prof = set()
            for token in data.get("capabilities", []) or []:
                cap_id, _ = self.registry.resolve(token)
                prof.add(cap_id or token)
            self.assertFalse(prof - declared[app_id],
                             "%s grants %s which the registry does not declare"
                             % (app_id, sorted(prof - declared[app_id])))

    def test_repo_review_has_no_hard_errors(self):
        facts = permd.kernel_facts(FIXTURE)
        store = permd.Store(self.tmp)
        report = permd.review(REPO, store, self.registry, facts=facts)
        for finding in report["findings"]:
            self.assertNotEqual(finding["severity"], "error", finding)

    def test_verify_permissions_repo_mode_passes(self):
        out = subprocess.run([sys.executable, VERIFY, "--store", self.tmp,
                              "--json", "--root", REPO],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        payload = json.loads(out.stdout.decode())
        self.assertEqual(payload["verdict"], "PASS", out.stdout.decode())
        self.assertEqual(out.returncode, 0, out.stderr.decode())
        self.assertEqual(payload["counts"]["mismatches"], 0)

    def test_verify_permissions_detects_a_missing_grant_in_device_mode(self):
        out = subprocess.run([sys.executable, VERIFY, "--store", self.tmp,
                              "--mode", "device", "--json", "--root", REPO],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        payload = json.loads(out.stdout.decode())
        self.assertEqual(payload["verdict"], "MISMATCH")
        self.assertEqual(out.returncode, 1)
        self.assertTrue(payload["mismatches"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
