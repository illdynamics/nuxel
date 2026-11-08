"""Backend adapter contract."""


class BackendError(RuntimeError):
    pass


class UnsupportedError(BackendError):
    pass


class BaseBackend:
    name = "base"
    supports_ipv6 = False
    supports_per_app = False
    per_app_mechanism = "none"

    def __init__(self, probe):
        self.probe = probe or {}

    # -- capability ---------------------------------------------------------
    def supported(self):
        return True

    def capability(self):
        return {
            "backend": self.name,
            "supported": self.supported(),
            "ipv4": True,
            "ipv6": self.supports_ipv6,
            "per_app": self.supports_per_app,
            "per_app_mechanism": self.per_app_mechanism,
        }

    # -- lifecycle ----------------------------------------------------------
    def snapshot(self):
        """Return an opaque, restorable representation of the current state."""
        raise NotImplementedError

    def render(self, policy, facts):
        """Return a plan object: {ipv4_commands, ipv6_commands, doc, warnings}."""
        raise NotImplementedError

    def validate(self, plan):
        """Syntax/API-check a plan WITHOUT mutating kernel state."""
        raise NotImplementedError

    def apply(self, plan):
        """Atomically apply a plan; raise on failure."""
        raise NotImplementedError

    def rollback(self, snapshot):
        """Restore a previous snapshot (Nuxel-owned objects only)."""
        raise NotImplementedError

    def readback(self):
        """Return the actual live ruleset text (for verification)."""
        raise NotImplementedError
