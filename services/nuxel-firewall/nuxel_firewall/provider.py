"""Bridge-facing provider: structured, validated methods only.

PWAs call named methods with structured arguments through the existing HTTP
bridge.  No arbitrary shell text, rule snippets, paths or unit names are ever
accepted from the UI.
"""
import json

from . import probe as probemod, remote as remotemod, schema, policy as policymod
from .backends import get_backend
from .transaction import FirewallManager, TransactionError
from .backends.base import UnsupportedError
from . import registry


class FirewallProvider:
    def __init__(self, policy_file=None, state_dir=None):
        import os
        from . import paths
        self.policy_file = policy_file or paths.POLICY_FILE
        self.state_dir = state_dir or paths.STATE_DIR
        os.makedirs(os.path.dirname(self.policy_file), exist_ok=True)
        os.makedirs(self.state_dir, exist_ok=True)

    # ------------------------------------------------------------- persistence
    def _load_policy(self):
        try:
            with open(self.policy_file) as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            raw = dict(schema.DEFAULT_POLICY)
        return schema.validate_policy(raw)

    def _save_policy(self, policy):
        tmp = self.policy_file + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(policy, fh, indent=2, sort_keys=True)
            fh.flush()
            import os
            os.fsync(fh.fileno())
        os.replace(tmp, self.policy_file)

    def _manager(self):
        policy = self._load_policy()
        probe = probemod.probe()
        name = probemod.selected_backend(policy.get("backend", "auto"), probe)
        if name == "none":
            raise TransactionError("no supported backend available")
        return get_backend(name, probe), probe, policy

    # ------------------------------------------------------------ read methods
    def get_status(self):
        probe = probemod.probe()
        policy = self._load_policy()
        name = "none"
        try:
            name = probemod.selected_backend(policy.get("backend", "auto"), probe)
        except RuntimeError as e:
            name = "conflict"
        return {
            "enabled": policy["enabled"],
            "backend": name,
            "defaults": policy["defaults"],
            "kernel_release": probe["kernel_release"],
            "backends": probe["backends"],
            "active_managers": probe["active_managers"],
            "per_app": probe["per_app"],
            "ipv4": policy["defaults"]["ipv4"],
            "ipv6": policy["defaults"]["ipv6"],
        }

    def get_backend_capabilities(self):
        probe = probemod.probe()
        policy = self._load_policy()
        name = "none"
        try:
            name = probemod.selected_backend(policy.get("backend", "auto"), probe)
        except RuntimeError:
            name = "conflict"
        try:
            cap = get_backend(name, probe).capability()
        except ValueError:
            cap = {"backend": name, "supported": False}
        cap.update({
            "kernel": {
                "nftables": probe["nftables_kernel"],
                "iptables": probe["iptables_kernel"],
                "ip6tables": probe["ip6tables_kernel"],
                "owner_match": probe["owner_match"],
                "cgroup_match": probe["cgroup_match"],
                "net_cls": probe["net_cls"],
            },
            "active_managers": probe["active_managers"],
        })
        return cap

    def get_installed_apps(self):
        apps = registry.canonical_apps()
        collisions = registry.classid_collisions(apps)
        probe = probemod.probe()
        # Honest per-app enforcement verdict for the whole runtime.
        per_app = probe["per_app"]
        enforceable = bool(per_app.get("enforceable_now"))
        for app in apps:
            app["network_enforcement"] = "verified" if enforceable else "unsupported"
        return {"apps": apps, "classid_collisions": collisions,
                "per_app_supported": enforceable,
                "per_app_mechanism": "uid-owner" if per_app["uid_owner"] else "none"}

    def get_interfaces(self):
        import subprocess
        try:
            r = subprocess.run(["ip", "-o", "link", "show"], capture_output=True,
                               text=True, timeout=6)
            links = r.stdout if r.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            links = ""
        return {"raw": links}

    def get_listeners(self):
        return remotemod.discover()

    def get_rules(self):
        policy = self._load_policy()
        return {"defaults": policy["defaults"], "services": policy["services"],
                "apps": policy["apps"]}

    def get_pending_transaction(self):
        try:
            backend, probe, _ = self._manager()
            return FirewallManager(backend, probe=probe,
                                   state_dir=self.state_dir).pending() or {}
        except Exception:
            return {}

    # --------------------------------------------------------- mutating methods
    def dry_run(self):
        backend, probe, policy = self._manager()
        facts = self._facts(policy)
        policy = dict(policy)
        policy["services"] = facts["services"]
        report = FirewallManager(backend, probe=probe,
                                 state_dir=self.state_dir).dry_run(policy, facts)
        report["per_app_supported"] = report.get("per_app_supported", False)
        return report

    def apply(self, rollback_after=None):
        backend, probe, policy = self._manager()
        facts = self._facts(policy)
        policy = dict(policy)
        policy["services"] = facts["services"]
        require_confirm = policy["safety"]["require_confirm"]
        result = FirewallManager(backend, probe=probe,
                                 state_dir=self.state_dir).apply(
            policy, facts, rollback_after=rollback_after, require_confirm=require_confirm)
        self._save_policy(dict(policy, enabled=True))
        return result

    def confirm(self):
        backend, probe, _ = self._manager()
        return FirewallManager(backend, probe=probe,
                               state_dir=self.state_dir).confirm()

    def rollback(self):
        backend, probe, _ = self._manager()
        return FirewallManager(backend, probe=probe,
                               state_dir=self.state_dir).rollback()

    def set_direction_default(self, direction, action):
        if direction not in ("input", "forward", "output"):
            raise ValueError("invalid direction")
        if action not in ("allow", "deny"):
            raise ValueError("invalid action")
        policy = self._load_policy()
        policy["defaults"][direction] = action
        self._save_policy(policy)
        return {"ok": True}

    def set_app_rule(self, app_id, outbound):
        schema.validate_app_id(app_id)
        if outbound not in ("inherit", "allow", "deny"):
            raise ValueError("invalid outbound")
        policy = self._load_policy()
        policy.setdefault("apps", {}).setdefault(app_id, {})["outbound"] = outbound
        self._save_policy(policy)
        return {"ok": True}

    def set_service_rule(self, service_id, source_cidrs, enabled):
        policy = self._load_policy()
        svc = policy.setdefault("services", {}).setdefault(service_id, {})
        for cidr in source_cidrs:
            schema.validate_ip(cidr)
        svc["source_cidrs"] = list(source_cidrs)
        svc["enabled"] = bool(enabled)
        self._save_policy(policy)
        return {"ok": True}

    def activate_profile(self, profile_id):
        policy = self._load_policy()
        new_policy = policymod.apply_profile(policy, profile_id)
        self._save_policy(new_policy)
        return {"ok": True}

    def enable(self):
        return self.apply()

    def disable(self):
        policy = self._load_policy()
        policy["enabled"] = False
        self._save_policy(policy)
        try:
            backend, probe, _ = self._manager()
            FirewallManager(backend, probe=probe, state_dir=self.state_dir).rollback()
        except Exception:
            pass
        return {"ok": True, "enabled": False}

    # ---------------------------------------------------------------- helpers
    def _facts(self, policy):
        discovered = remotemod.discover()
        services = remotemod.build_service_policies(discovered, policy.get("services", {}))
        return {"remote": discovered, "services": services, "app_uids": {}}
