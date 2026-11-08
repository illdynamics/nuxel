"""firewalld adapter — global/service controls via its supported D-Bus API.

Per-app (AFWall-style) matrix is NOT supported under firewalld unless a tested
cgroup/UID mechanism is integrated without conflicting with the owner.  Mutating
methods therefore refuse and report the capability honestly.
"""
from .base import BaseBackend, UnsupportedError


class FirewalldBackend(BaseBackend):
    name = "firewalld"
    supports_ipv6 = True
    supports_per_app = False
    per_app_mechanism = "none"

    def supported(self):
        return bool(self.probe.get("active_managers", {}).get("firewalld"))

    def render(self, policy, facts):
        raise UnsupportedError(
            "firewalld mutation is not implemented in this release; the adapter "
            "reports global/service controls as unsupported and per-app as unavailable")

    def validate(self, plan):
        raise UnsupportedError("firewalld validate not implemented")

    def apply(self, plan):
        raise UnsupportedError("firewalld apply not implemented")

    def rollback(self, snapshot):
        raise UnsupportedError("firewalld rollback not implemented")

    def readback(self):
        return {"firewall-cmd": "not implemented"}
