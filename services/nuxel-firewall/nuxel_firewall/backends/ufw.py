"""UFW adapter — global/service controls via its supported CLI.

UFW application profiles are service/port descriptions, not per-process app
identity, so per-app matrix is honestly unsupported.  Mutation is not
implemented in this release and refuses instead of faking success.
"""
from .base import BaseBackend, UnsupportedError


class UFWBackend(BaseBackend):
    name = "ufw"
    supports_ipv6 = True
    supports_per_app = False
    per_app_mechanism = "none"

    def supported(self):
        return bool(self.probe.get("active_managers", {}).get("ufw"))

    def render(self, policy, facts):
        raise UnsupportedError("UFW mutation is not implemented in this release")

    def validate(self, plan):
        raise UnsupportedError("UFW validate not implemented")

    def apply(self, plan):
        raise UnsupportedError("UFW apply not implemented")

    def rollback(self, snapshot):
        raise UnsupportedError("UFW rollback not implemented")

    def readback(self):
        return {"ufw": "not implemented"}
