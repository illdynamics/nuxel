import copy
import json
import os
import tempfile
import unittest

from nuxel_firewall import schema
from nuxel_firewall.transaction import FirewallManager, TransactionError


class MockBackend:
    name = "mock"
    supports_ipv6 = True
    supports_per_app = False
    per_app_mechanism = "none"
    applied = False
    rolled_back = False
    snapshots = []

    def __init__(self, probe=None):
        self.probe = probe or {}

    def capability(self):
        return {"backend": self.name, "supported": True, "ipv4": True,
                "ipv6": True, "per_app": False, "per_app_mechanism": "none"}

    def snapshot(self):
        self.snapshots.append("snap")
        return {"state": "prior"}

    def render(self, policy, facts):
        return {"ipv4": [], "ipv6": [], "warnings": [],
                "per_app_supported": False, "doc": ""}

    def validate(self, plan):
        return True

    def apply(self, plan):
        self.applied = True

    def rollback(self, snapshot):
        self.rolled_back = True

    def readback(self):
        return {"mock": "-A NUXEL_FW_INPUT -p tcp --dport 22 -s 192.168.178.0/24 -j ACCEPT"}


def _policy():
    p = schema.validate_policy(copy.deepcopy(schema.DEFAULT_POLICY))
    p["services"]["nuxel-ssh-owner"] = {
        "protocol": "tcp", "port": 22, "source_cidrs": ["192.168.178.0/24"],
        "enabled": True, "active": True, "interfaces": [], "bind_addresses": [],
        "security_note": "",
    }
    return p


class TestTransaction(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.backend = MockBackend()
        self.fired = []
        self.mgr = FirewallManager(self.backend, probe={}, state_dir=self.tmp,
                                   timer=lambda txid, sec: self.fired.append((txid, sec)),
                                   now=lambda: 1000.0)

    def test_dry_run_no_mutation(self):
        before = list(self.backend.snapshots)
        report = self.mgr.dry_run(_policy(), {"app_uids": {}, "services": {}})
        self.assertFalse(self.backend.applied)
        self.assertEqual(list(self.backend.snapshots), before)
        self.assertIn("management_rules", report)

    def test_apply_refuses_without_ssh_allowlist(self):
        p = _policy()
        p["services"]["nuxel-ssh-owner"]["enabled"] = False
        with self.assertRaises(TransactionError):
            self.mgr.apply(p, {"app_uids": {}, "services": {}})

    def test_apply_arms_timer_before_mutation_and_confirm(self):
        result = self.mgr.apply(_policy(), {"app_uids": {}, "services": {}})
        self.assertEqual(self.fired, [(result["txid"], 60)])
        self.assertTrue(self.backend.applied)
        self.assertFalse(self.backend.rolled_back)
        self.assertTrue(self.mgr.pending())
        self.mgr.confirm()
        self.assertIsNone(self.mgr.pending())
        self.assertTrue(self.mgr.last_known_good())

    def test_rollback_restores(self):
        self.mgr.apply(_policy(), {"app_uids": {}, "services": {}})
        self.mgr.rollback()
        self.assertTrue(self.backend.rolled_back)
        self.assertIsNone(self.mgr.pending())

    def test_boot_recovery_with_pending(self):
        self.mgr.apply(_policy(), {"app_uids": {}, "services": {}})
        self.assertTrue(self.mgr.pending())
        # A new manager instance (as after reboot) sees the pending state.
        mgr2 = FirewallManager(self.backend, probe={}, state_dir=self.tmp,
                               timer=lambda t, s: None, now=lambda: 9999.0)
        out = mgr2.boot_recover()
        self.assertTrue(out["recovered"])
        self.assertTrue(self.backend.rolled_back)


if __name__ == "__main__":
    unittest.main()
