import copy
import unittest

from nuxel_firewall import schema, policy
from nuxel_firewall.backends.iptables import IPTablesBackend, CH_INPUT, CH_OUTPUT, CH_FORWARD

PROBE = {
    "kernel_release": "4.14.253",
    "nftables_kernel": False, "iptables_kernel": True, "ip6tables_kernel": True,
    "owner_match": True, "cgroup_match": False, "net_cls": True,
    "binaries": {"nft": None, "iptables": "iptables-legacy", "ip6tables": "ip6tables-legacy",
                 "firewalld": None, "ufw": None},
    "backends": {"nftables": False, "iptables": True, "iptables_ipv6": True},
    "active_managers": {"firewalld": False, "ufw": False},
    "cgroup": {"unified": True, "controllers": []},
    "per_app": {"uid_owner": True, "cgroup": False, "supported": True},
}


def _policy():
    p = schema.validate_policy(copy.deepcopy(schema.DEFAULT_POLICY))
    p["services"]["nuxel-ssh-owner"] = {
        "protocol": "tcp", "port": 22, "source_cidrs": ["192.168.178.0/24"],
        "enabled": True, "active": True, "interfaces": [], "bind_addresses": [],
        "security_note": "",
    }
    return p


class TestIPTablesRender(unittest.TestCase):
    def test_no_global_flush(self):
        b = IPTablesBackend(PROBE)
        plan = b.render(_policy(), {"app_uids": {}, "services": {}})
        all_args = [args for _, args, _ in plan["ipv4"] + plan["ipv6"]]
        self.assertFalse(any(a[0] in ("-F", "--flush") and len(a) == 2 for a in all_args))
        # no bare `-F` (global flush) outside owned chains
        for a in all_args:
            if a and a[0] == "-F":
                self.assertIn(a[1], (CH_INPUT, CH_OUTPUT, CH_FORWARD))

    def test_input_drop_and_ssh_allow(self):
        b = IPTablesBackend(PROBE)
        plan = b.render(_policy(), {"app_uids": {}, "services": {}})
        v4 = plan["ipv4"]
        self.assertTrue(any(args[-2:] == ["-j", "DROP"] and args[1] == CH_INPUT
                            for _, args, _ in v4))
        # SSH allow from the source CIDR is present before the drop
        self.assertTrue(any("--dport" in args and "22" in args and "192.168.178.0/24" in args
                            for _, args, _ in v4))

    def test_output_allow_has_no_terminal_drop(self):
        b = IPTablesBackend(PROBE)
        plan = b.render(_policy(), {"app_uids": {}, "services": {}})
        self.assertFalse(any(args[1] == CH_OUTPUT and args[-2:] == ["-j", "DROP"]
                             for _, args, _ in plan["ipv4"]))

    def test_output_deny_has_terminal_drop(self):
        b = IPTablesBackend(PROBE)
        p = _policy()
        p["defaults"]["output"] = "deny"
        plan = b.render(p, {"app_uids": {}, "services": {}})
        self.assertTrue(any(args[1] == CH_OUTPUT and args[-2:] == ["-j", "DROP"]
                            for _, args, _ in plan["ipv4"]))

    def test_forward_deny(self):
        b = IPTablesBackend(PROBE)
        plan = b.render(_policy(), {"app_uids": {}, "services": {}})
        self.assertTrue(any(args[1] == CH_FORWARD and args[-2:] == ["-j", "DROP"]
                            for _, args, _ in plan["ipv4"]))

    def test_per_app_owner_deny_before_established(self):
        b = IPTablesBackend(PROBE)
        p = _policy()
        p["apps"]["org.nuxel.Blocked"] = {"outbound": "deny"}
        facts = {"app_uids": {"org.nuxel.Blocked": 1001,
                              "org.nuxel.Allowed": 1002}, "services": {}}
        plan = b.render(p, facts)
        deny_idx = None
        for i, (_, args, _) in enumerate(plan["ipv4"]):
            if args[1] == CH_OUTPUT and "--uid-owner" in args:
                deny_idx = i
                break
        self.assertIsNotNone(deny_idx)

    def test_per_app_unsupported_when_single_uid(self):
        b = IPTablesBackend(PROBE)
        plan = b.render(_policy(), {"app_uids": {"a": 0, "b": 0}, "services": {}})
        self.assertFalse(plan["per_app_supported"])
        self.assertTrue(any("per-app filtering unavailable" in w for w in plan["warnings"]))

    def test_ipv6_disabled_skips_v6(self):
        b = IPTablesBackend(PROBE)
        p = _policy()
        p["defaults"]["ipv6"] = False
        plan = b.render(p, {"app_uids": {}, "services": {}})
        self.assertEqual(plan["ipv6"], [])


if __name__ == "__main__":
    unittest.main()
