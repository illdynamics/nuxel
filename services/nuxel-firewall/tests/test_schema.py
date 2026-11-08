import copy
import unittest

from nuxel_firewall import schema


class TestSchema(unittest.TestCase):
    def test_default_policy_valid(self):
        p = schema.validate_policy(copy.deepcopy(schema.DEFAULT_POLICY))
        self.assertEqual(p["defaults"]["output"], "allow")

    def test_rejects_unknown_key(self):
        p = copy.deepcopy(schema.DEFAULT_POLICY)
        p["bogus"] = True
        with self.assertRaises(schema.PolicyValidationError):
            schema.validate_policy(p)

    def test_rejects_bad_direction(self):
        p = copy.deepcopy(schema.DEFAULT_POLICY)
        p["defaults"]["output"] = "maybe"
        with self.assertRaises(schema.PolicyValidationError):
            schema.validate_policy(p)

    def test_cidr_validation(self):
        self.assertEqual(schema.validate_ip("192.168.1.0/24"), "192.168.1.0/24")
        with self.assertRaises(schema.PolicyValidationError):
            schema.validate_ip("999.1.1.1/24")
        with self.assertRaises(schema.PolicyValidationError):
            schema.validate_ip("not-an-ip")

    def test_port_validation(self):
        self.assertEqual(schema.validate_port("22"), 22)
        self.assertEqual(schema.validate_port(3389), 3389)
        with self.assertRaises(schema.PolicyValidationError):
            schema.validate_port(70000)
        with self.assertRaises(schema.PolicyValidationError):
            schema.validate_port("abc")

    def test_app_id_collision(self):
        p = copy.deepcopy(schema.DEFAULT_POLICY)
        p["apps"] = {"Org.Nuxel.App": {"outbound": "deny"},
                     "org.nuxel.app": {"outbound": "allow"}}
        with self.assertRaises(schema.PolicyValidationError):
            schema.validate_policy(p)

    def test_service_rule_validation(self):
        p = copy.deepcopy(schema.DEFAULT_POLICY)
        p["services"]["s"] = {"protocol": "tcp", "port": 22,
                              "source_cidrs": ["10.0.0.0/8"]}
        out = schema.validate_policy(p)
        self.assertEqual(out["services"]["s"]["source_cidrs"], ["10.0.0.0/8"])
        p["services"]["s"]["protocol"] = "quic"
        with self.assertRaises(schema.PolicyValidationError):
            schema.validate_policy(p)


if __name__ == "__main__":
    unittest.main()
