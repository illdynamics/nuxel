"""Native iptables (xtables) backend — the only kernel-usable backend on S10+.

The S10+ Linux 4.14.253 kernel has nftables DISABLED (`CONFIG_NF_TABLES is not
set`) but ships xtables built-in for IPv4 + IPv6.  This adapter manages only
Nuxel-owned chains in the `filter` table and never issues a global flush.

Per-app attribution is via `-m owner --uid-owner` ONLY when apps run under
distinct UIDs.  On the live handset every UI/WebKit process runs as root, so the
backend honestly reports per-app as unsupported there.
"""
import shutil
import subprocess

from .base import BaseBackend, BackendError, UnsupportedError

CH_INPUT = "NUXEL_FW_INPUT"
CH_OUTPUT = "NUXEL_FW_OUTPUT"
CH_FORWARD = "NUXEL_FW_FORWARD"
OWNED_CHAINS = (CH_INPUT, CH_OUTPUT, CH_FORWARD)
JUMP_COMMENT = "nuxel-firewall"

ICMP4_ESSENTIAL = ("echo-request", "echo-reply", "destination-unreachable",
                   "time-exceeded", "parameter-problem")
ICMP6_ESSENTIAL = ("destination-unreachable", "time-exceeded", "parameter-problem",
                   "echo-request", "echo-reply", "neighbor-solicit",
                   "neighbor-advertise", "router-solicit", "router-advertise")


def _cmd(bin_, args, best_effort=False):
    return (bin_, args, best_effort)


class IPTablesBackend(BaseBackend):
    name = "iptables"
    supports_ipv6 = True

    def __init__(self, probe=None):
        super().__init__(probe)
        p = probe or {}
        self._v4_bin = self._resolve("iptables-legacy", "iptables")
        self._v6_bin = self._resolve("ip6tables-legacy", "ip6tables")
        self._v6_ok = bool(p.get("backends", {}).get("iptables_ipv6"))
        self.per_app_mechanism = "uid-owner" if p.get("owner_match") else "none"
        self.supports_per_app = bool(p.get("owner_match"))

    @staticmethod
    def _resolve(*names):
        for n in names:
            found = shutil.which(n)
            if found:
                return found
        return names[0]

    def supported(self):
        return bool(shutil.which("iptables-legacy") or shutil.which("iptables"))

    # ---------------------------------------------------------------- render
    def render(self, policy, facts):
        defaults = policy["defaults"]
        warnings = []
        plan = {"ipv4": [], "ipv6": [], "warnings": warnings,
                "per_app_supported": False, "doc": self._doc(policy), "foreign": {}}

        v4, v6 = self._chain_prelude(self._v4_bin), self._chain_prelude(self._v6_bin)

        # Insert jump rules at position 1 (after prelude; must succeed).
        for builtin, target in (("INPUT", CH_INPUT), ("OUTPUT", CH_OUTPUT),
                                ("FORWARD", CH_FORWARD)):
            v4.append(_cmd(self._v4_bin, ["-t", "filter", "-I", builtin, "1",
                                          "-m", "comment", "--comment", JUMP_COMMENT,
                                          "-j", target]))
            v6.append(_cmd(self._v6_bin, ["-t", "filter", "-I", builtin, "1",
                                          "-m", "comment", "--comment", JUMP_COMMENT,
                                          "-j", target]))

        v4 += self._input_rules(policy, ipv6=False, warnings=warnings)
        v6 += self._input_rules(policy, ipv6=True, warnings=warnings)
        v4 += self._forward_rules(policy, ipv6=False)
        v6 += self._forward_rules(policy, ipv6=True)
        v4 += self._output_rules(policy, facts, ipv6=False, warnings=warnings)
        v6 += self._output_rules(policy, facts, ipv6=True, warnings=warnings)

        if not defaults["ipv4"]:
            v4 = []
        if not defaults["ipv6"] or not self._v6_ok:
            v6 = []

        plan["ipv4"] = v4
        plan["ipv6"] = v6
        plan["per_app_supported"] = self._per_app_usable(facts)
        return plan

    def _chain_prelude(self, bin_):
        """Remove prior jump refs and prior chains, then recreate (idempotent)."""
        out = []
        for builtin, target in (("INPUT", CH_INPUT), ("OUTPUT", CH_OUTPUT),
                                ("FORWARD", CH_FORWARD)):
            out.append(_cmd(bin_, ["-t", "filter", "-D", builtin,
                                   "-m", "comment", "--comment", JUMP_COMMENT,
                                   "-j", target], best_effort=True))
        for chain in OWNED_CHAINS:
            out.append(_cmd(bin_, ["-t", "filter", "-F", chain], best_effort=True))
            out.append(_cmd(bin_, ["-t", "filter", "-X", chain], best_effort=True))
            out.append(_cmd(bin_, ["-t", "filter", "-N", chain]))
        return out

    def _input_rules(self, policy, ipv6, warnings):
        bin_ = self._v6_bin if ipv6 else self._v4_bin
        chain = CH_INPUT
        rules = []
        if policy["defaults"]["input"] == "allow":
            return rules
        rules.append(_cmd(bin_, ["-A", chain, "-m", "conntrack",
                                 "--ctstate", "ESTABLISHED,RELATED", "-j", "ACCEPT"]))
        rules.append(_cmd(bin_, ["-A", chain, "-i", "lo", "-j", "ACCEPT"]))
        if ipv6:
            rules.append(_cmd(bin_, ["-A", chain, "-p", "udp", "--sport", "547",
                                     "--dport", "546", "-j", "ACCEPT"]))
        else:
            rules.append(_cmd(bin_, ["-A", chain, "-p", "udp", "--sport", "67",
                                     "--dport", "68", "-j", "ACCEPT"]))
        for t in (ICMP6_ESSENTIAL if ipv6 else ICMP4_ESSENTIAL):
            icmp_arg = ["--icmpv6-type", t] if ipv6 else ["--icmp-type", t]
            rules.append(_cmd(bin_, ["-A", chain, "-p", "ipv6-icmp" if ipv6 else "icmp"]
                                   + icmp_arg + ["-m", "limit", "--limit", "10/second",
                                                 "-j", "ACCEPT"]))
        rules += self._service_rules(bin_, chain, policy, ipv6, warnings)
        if policy["logging"].get("blocked_log"):
            rules.append(_cmd(bin_, ["-A", chain, "-m", "limit", "--limit",
                                     policy["logging"].get("rate", "10/minute"),
                                     "-j", "LOG", "--log-prefix", "NUXEL-INPUT-DROP: "]))
        rules.append(_cmd(bin_, ["-A", chain, "-j", "DROP"]))
        return rules

    def _forward_rules(self, policy, ipv6):
        bin_ = self._v6_bin if ipv6 else self._v4_bin
        if policy["defaults"]["forward"] == "allow":
            return []
        return [_cmd(bin_, ["-A", CH_FORWARD, "-j", "DROP"])]

    def _output_rules(self, policy, facts, ipv6, warnings):
        bin_ = self._v6_bin if ipv6 else self._v4_bin
        chain = CH_OUTPUT
        rules = []
        per_app = self._per_app_plan(policy, facts, ipv6, warnings)
        if policy["defaults"]["output"] == "allow":
            return per_app["deny_rules"]
        rules.append(_cmd(bin_, ["-A", chain, "-o", "lo", "-j", "ACCEPT"]))
        rules += per_app["allow_rules"]
        if ipv6:
            rules.append(_cmd(bin_, ["-A", chain, "-p", "udp", "--dport", "547",
                                     "--sport", "546", "-j", "ACCEPT"]))
            for t in ICMP6_ESSENTIAL:
                rules.append(_cmd(bin_, ["-A", chain, "-p", "ipv6-icmp",
                                         "--icmpv6-type", t, "-j", "ACCEPT"]))
        else:
            rules.append(_cmd(bin_, ["-A", chain, "-p", "udp", "--dport", "67",
                                     "--sport", "68", "-j", "ACCEPT"]))
        if policy["logging"].get("blocked_log"):
            rules.append(_cmd(bin_, ["-A", chain, "-m", "limit", "--limit",
                                     policy["logging"].get("rate", "10/minute"),
                                     "-j", "LOG", "--log-prefix", "NUXEL-OUTPUT-DROP: "]))
        rules.append(_cmd(bin_, ["-A", chain, "-j", "DROP"]))
        return rules

    def _service_rules(self, bin_, chain, policy, ipv6, warnings):
        rules = []
        for sid, svc in (policy.get("services") or {}).items():
            if not svc.get("enabled") or not svc.get("active"):
                continue
            ports = svc.get("port", 22)
            if isinstance(ports, int):
                ports = [ports]
            sources = svc.get("source_cidrs") or []
            if not sources:
                warnings.append("service %s enabled but has no source CIDRs; skipped" % sid)
                continue
            for port in ports:
                for cidr in sources:
                    if (":" in cidr) != ipv6:
                        continue
                    args = ["-A", chain, "-p", svc.get("protocol", "tcp"),
                            "--dport", str(port), "-s", cidr, "-j", "ACCEPT"]
                    rules.append(_cmd(bin_, args))
        return rules

    def _per_app_usable(self, facts):
        uids = (facts or {}).get("app_uids")
        if not uids or not self.supports_per_app:
            return False
        distinct = set(uids.values())
        return len(distinct) > 1

    def _per_app_plan(self, policy, facts, ipv6, warnings):
        deny_rules = []
        allow_rules = []
        if not self._per_app_usable(facts):
            if facts and facts.get("app_uids") and not self._per_app_usable(facts):
                warnings.append(
                    "per-app filtering unavailable: apps share a single UID (root); "
                    "assign distinct UIDs to enable owner-UID rules")
            return {"deny_rules": deny_rules, "allow_rules": allow_rules}
        bin_ = self._v6_bin if ipv6 else self._v4_bin
        from ..policy import app_outbound
        uids = facts["app_uids"]
        for app_id, uid in uids.items():
            decision = app_outbound(policy, app_id)
            if decision == "deny":
                deny_rules.append(_cmd(bin_, ["-A", CH_OUTPUT, "-m", "owner",
                                              "--uid-owner", str(uid), "-j", "DROP"]))
            elif policy["defaults"]["output"] == "deny" and decision == "allow":
                allow_rules.append(_cmd(bin_, ["-A", CH_OUTPUT, "-m", "owner",
                                               "--uid-owner", str(uid), "-j", "ACCEPT"]))
        return {"deny_rules": deny_rules, "allow_rules": allow_rules}

    # ------------------------------------------------------------- lifecycle
    def snapshot(self):
        snap = {}
        for label, bin_ in (("ipv4", self._v4_bin), ("ipv6", self._v6_bin)):
            snap[label] = self._run_capture(bin_, ["-S"])
        return snap

    def validate(self, plan):
        missing = []
        for bin_ in (self._v4_bin, self._v6_bin):
            if not shutil.which(bin_):
                missing.append(bin_)
        if missing:
            raise UnsupportedError("iptables binaries unavailable: %s" % ", ".join(missing))
        # Programmatically-generated commands; validate binary can run at all.
        self._run(self._v4_bin, ["--version"])
        return True

    def apply(self, plan):
        self._run_many(plan.get("ipv4", []))
        self._run_many(plan.get("ipv6", []))

    def rollback(self, snapshot):
        for bin_ in (self._v4_bin, self._v6_bin):
            for builtin, target in (("INPUT", CH_INPUT), ("OUTPUT", CH_OUTPUT),
                                    ("FORWARD", CH_FORWARD)):
                self._run_best_effort(bin_, ["-t", "filter", "-D", builtin,
                                             "-m", "comment", "--comment", JUMP_COMMENT,
                                             "-j", target])
            for chain in OWNED_CHAINS:
                self._run_best_effort(bin_, ["-t", "filter", "-F", chain])
                self._run_best_effort(bin_, ["-t", "filter", "-X", chain])

    def readback(self):
        out = {}
        for label, bin_ in (("ipv4", self._v4_bin), ("ipv6", self._v6_bin)):
            out[label] = self._run_capture(bin_, ["-S"])
        return out

    # ------------------------------------------------------------------ util
    def _run_many(self, commands):
        for bin_, args, best_effort in commands:
            if best_effort:
                self._run_best_effort(bin_, args)
            else:
                self._run(bin_, args)

    @staticmethod
    def _run_capture(bin_, args):
        try:
            r = subprocess.run([bin_] + args, capture_output=True, text=True, timeout=15)
            return r.stdout if r.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            return ""

    @staticmethod
    def _run(bin_, args):
        try:
            r = subprocess.run([bin_] + args, capture_output=True, text=True, timeout=15)
        except OSError as e:
            raise BackendError("failed to run %s: %s" % (bin_, e))
        if r.returncode != 0:
            raise BackendError("%s %s failed: %s" % (bin_, " ".join(args), r.stderr.strip()))

    @staticmethod
    def _run_best_effort(bin_, args):
        try:
            subprocess.run([bin_] + args, capture_output=True, text=True, timeout=15)
        except OSError:
            pass

    # ------------------------------------------------------------------- doc
    @staticmethod
    def _doc(policy):
        lines = ["# Nuxel firewall — iptables backend plan (filter table, owned chains only)",
                 "# Inspection view. Applied via scoped iptables/ip6tables commands, never a full-table replace.",
                 "*filter"]
        for builtin in ("INPUT", "FORWARD", "OUTPUT"):
            lines.append(":%s ACCEPT [0:0]" % builtin)
        for chain in OWNED_CHAINS:
            lines.append(":%s - [0:0]" % chain)
        lines.append("-I INPUT 1 -m comment --comment %s -j %s" % (JUMP_COMMENT, CH_INPUT))
        lines.append("-I OUTPUT 1 -m comment --comment %s -j %s" % (JUMP_COMMENT, CH_OUTPUT))
        lines.append("-I FORWARD 1 -m comment --comment %s -j %s" % (JUMP_COMMENT, CH_FORWARD))
        for sid, svc in (policy.get("services") or {}).items():
            if svc.get("enabled") and svc.get("active"):
                for cidr in (svc.get("source_cidrs") or []):
                    lines.append("-A %s -p %s --dport %s -s %s -j ACCEPT" % (
                        CH_INPUT, svc.get("protocol", "tcp"), svc.get("port", 22), cidr))
        defaults = policy["defaults"]
        lines.append("-A %s -j %s" % (CH_INPUT, "DROP" if defaults["input"] == "deny" else "RETURN"))
        lines.append("-A %s -j %s" % (CH_FORWARD, "DROP" if defaults["forward"] == "deny" else "RETURN"))
        lines.append("-A %s -j %s" % (CH_OUTPUT, "DROP" if defaults["output"] == "deny" else "RETURN"))
        lines.append("COMMIT")
        return "\n".join(lines)
