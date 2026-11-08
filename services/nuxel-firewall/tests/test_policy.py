import copy
import unittest

from nuxel_firewall import schema, policy


class TestPolicy(unittest.TestCase):
    def _policy(self):
        return schema.validate_policy(copy.deepcopy(schema.DEFAULT_POLICY))

    def test_global_default_output_allow(self):
        p = self._policy()
        self.assertEqual(policy.global_outbound_default(p), "allow")
        self.assertEqual(policy.app_outbound(p, "any.app"), "allow")

    def test_strict_mode_inherits_deny(self):
        p = self._policy()
        p["defaults"]["output"] = "deny"
        self.assertEqual(policy.app_outbound(p, "any.app"), "deny")

    def test_explicit_deny_overrides_allow_default(self):
        p = self._policy()
        p["apps"]["org.nuxel.Isolated"] = {"outbound": "deny"}
        self.assertEqual(policy.app_outbound(p, "org.nuxel.Isolated"), "deny")

    def test_network_override(self):
        p = self._policy()
        p["apps"]["a"] = {"outbound": "allow", "networks": {"cellular": "deny"}}
        self.assertEqual(policy.app_network_decision(p, "a", "wifi"), "allow")
        self.assertEqual(policy.app_network_decision(p, "a", "cellular"), "deny")

    def test_new_app_inherit(self):
        p = self._policy()
        p["defaults"]["output"] = "deny"
        self.assertEqual(policy.new_app_decision(p), "deny")

    def test_migrate_preserves_legacy_blocks(self):
        p = self._policy()
        legacy = {"nuxel-contacts": {"network_class": "isolated"},
                  "nuxel-dialer": {"network_class": "public"},
                  "nuxel-new": {}}
        migrated, counts = policy.migrate_legacy_overrides(p, legacy)
        self.assertEqual(migrated["apps"]["nuxel-contacts"]["outbound"], "deny")
        self.assertEqual(migrated["apps"]["nuxel-dialer"]["outbound"], "allow")
        self.assertEqual(counts["preserved_deny"], 1)
        self.assertEqual(counts["preserved_allow"], 1)
        self.assertEqual(counts["inheriting"], 1)

    def test_profile_strict(self):
        p = self._policy()
        p2 = policy.apply_profile(p, "strict-outbound")
        self.assertEqual(p2["defaults"]["output"], "deny")


if __name__ == "__main__":
    unittest.main()
