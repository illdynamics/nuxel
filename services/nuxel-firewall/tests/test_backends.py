import copy
import unittest

from nuxel_firewall import schema
from nuxel_firewall.backends.nftables import NFTablesBackend
from nuxel_firewall.backends.firewalld import FirewalldBackend
from nuxel_firewall.backends.ufw import UFWBackend
from nuxel_firewall.backends.base import UnsupportedError


def _policy():
    return schema.validate_policy(copy.deepcopy(schema.DEFAULT_POLICY))


class TestNFTablesBackend(unittest.TestCase):
    def test_unsupported_when_kernel_lacks_nftables(self):
        b = NFTablesBackend({"nftables_kernel": False})
        self.assertFalse(b.supported())
        with self.assertRaises(UnsupportedError):
            b.render(_policy(), {})

    def test_corrected_ruleset_no_flush_and_single_chain(self):
        b = NFTablesBackend({"nftables_kernel": True, "binaries": {"nft": "nft"}})
        plan = b.render(_policy(), {})
        rs = plan["nft"]
        self.assertFalse(any(l.strip() == "flush ruleset" for l in rs.splitlines()))
        self.assertIn("table inet nuxel_firewall", rs)
        self.assertIn("type filter hook input priority -100; policy drop;", rs)
        self.assertIn("type filter hook forward priority -100; policy drop;", rs)
        self.assertIn("type filter hook output priority -100; policy accept;", rs)

    def test_nftables_output_deny_in_strict(self):
        p = _policy()
        p["defaults"]["output"] = "deny"
        b = NFTablesBackend({"nftables_kernel": True, "binaries": {"nft": "nft"}})
        rs = b.render(p, {})["nft"]
        self.assertIn("type filter hook output priority -100; policy drop;", rs)


class TestDetectionOnlyBackends(unittest.TestCase):
    def test_firewalld_refuses_mutation(self):
        b = FirewalldBackend({"active_managers": {"firewalld": True}})
        with self.assertRaises(UnsupportedError):
            b.render(_policy(), {})

    def test_ufw_refuses_mutation(self):
        b = UFWBackend({"active_managers": {"ufw": True}})
        with self.assertRaises(UnsupportedError):
            b.render(_policy(), {})


if __name__ == "__main__":
    unittest.main()
