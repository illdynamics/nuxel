"""Native nftables backend (preferred on kernels that enable CONFIG_NF_TABLES).

Corrected architecture vs. the legacy repo ruleset:
  * no `flush ruleset`;
  * a single authoritative Nuxel base chain per hook inside `inet nuxel_firewall`;
  * service exceptions and app policy integrated into the same policy path, not
    an early-accept guard chain that a later base chain can still drop.

On the S10+ this backend reports supported=False because the kernel ships
`CONFIG_NF_TABLES is not set`.
"""
from .base import BaseBackend, UnsupportedError


class NFTablesBackend(BaseBackend):
    name = "nftables"
    supports_ipv6 = True
    per_app_mechanism = "none"

    def __init__(self, probe=None):
        super().__init__(probe)
        p = probe or {}
        self._kernel_ok = bool(p.get("nftables_kernel"))
        self._bin = (p.get("binaries") or {}).get("nft", "nft")
        self.supports_per_app = False  # requires socket cgroupv2 (>= 5.13) not on 4.14

    def supported(self):
        return self._kernel_ok

    def capability(self):
        cap = super().capability()
        cap["supported"] = self.supported()
        cap["reason"] = "" if self.supported() else "kernel has CONFIG_NF_TABLES not set"
        return cap

    def render(self, policy, facts):
        if not self.supported():
            raise UnsupportedError(
                "nftables unavailable: kernel has CONFIG_NF_TABLES not set")
        return {"nft": self._ruleset(policy, facts), "warnings": []}

    def validate(self, plan):
        # `nft -c -f` validates syntax without changing kernel state.
        import subprocess, tempfile, os
        with tempfile.NamedTemporaryFile("w", suffix=".nft", delete=False) as fh:
            fh.write(plan["nft"])
            path = fh.name
        try:
            r = subprocess.run([self._bin, "-c", "-f", path],
                               capture_output=True, text=True, timeout=15)
            if r.returncode != 0:
                raise UnsupportedError("nft -c failed: %s" % r.stderr.strip())
        finally:
            os.unlink(path)
        return True

    def _ruleset(self, policy, facts):
        defaults = policy["defaults"]
        inp = "drop" if defaults["input"] == "deny" else "accept"
        fwd = "drop" if defaults["forward"] == "deny" else "accept"
        out = "accept" if defaults["output"] == "allow" else "drop"
        lines = [
            "# Nuxel firewall — native nftables (corrected architecture)",
            "# No `flush ruleset`. Single authoritative base chain per hook.",
            "table inet nuxel_firewall {",
            "  chain input {",
            "    type filter hook input priority -100; policy %s;" % inp,
            "    ct state established,related accept",
            "    iif lo accept",
        ]
        for sid, svc in (policy.get("services") or {}).items():
            if svc.get("enabled") and svc.get("active"):
                for cidr in (svc.get("source_cidrs") or []):
                    lines.append("    %s dport %s ip saddr %s accept" % (
                        svc.get("protocol", "tcp"), svc.get("port", 22), cidr))
        lines += [
            "    ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded, parameter-problem } limit rate 10/second accept",
            "    ip6 nexthdr icmpv6 icmpv6 type { nd-neighbor-solicit, nd-neighbor-advert, nd-router-solicit, nd-router-advert, destination-unreachable, time-exceeded } accept",
            "  }",
            "  chain forward {",
            "    type filter hook forward priority -100; policy %s;" % fwd,
            "  }",
            "  chain output {",
            "    type filter hook output priority -100; policy %s;" % out,
            "    oif lo accept",
            "  }",
            "}",
        ]
        return "\n".join(lines)
