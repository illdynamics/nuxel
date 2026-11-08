"""nuxel-firewall CLI — recovery + diagnostics, same safety path as the UI."""
import argparse
import json
import os
import sys

from . import paths, schema, policy as policymod, probe as probemod, remote as remotemod
from .backends import get_backend
from .transaction import FirewallManager, TransactionError
from .backends.base import UnsupportedError


def _load_policy():
    try:
        with open(paths.POLICY_FILE) as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        raw = dict(schema.DEFAULT_POLICY)
    return schema.validate_policy(raw)


def _save_policy(policy):
    paths.ensure_dirs()
    tmp = paths.POLICY_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(policy, fh, indent=2, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, paths.POLICY_FILE)


def _facts():
    discovered = remotemod.discover()
    policy = _load_policy()
    services = remotemod.build_service_policies(discovered, policy.get("services", {}))
    return {
        "remote": discovered,
        "services": services,
        "app_uids": {},  # populated only when per-app UIDs exist (see registry)
    }


def _manager(policy=None):
    policy = policy or _load_policy()
    probe = probemod.probe()
    backend_name = probemod.selected_backend(policy.get("backend", "auto"), probe)
    if backend_name == "none":
        raise TransactionError(
            "no supported firewall backend available (kernel lacks nftables and "
            "no iptables binary is installed)")
    backend = get_backend(backend_name, probe)
    return backend, probe, policy


def cmd_status(_):
    probe = probemod.probe()
    policy = _load_policy()
    print(json.dumps({
        "kernel_release": probe["kernel_release"],
        "backends": probe["backends"],
        "active_managers": probe["active_managers"],
        "per_app": probe["per_app"],
        "policy": policy["defaults"],
        "enabled": policy["enabled"],
    }, indent=2, sort_keys=True))


def cmd_backend_probe(_):
    print(json.dumps(probemod.probe(), indent=2, sort_keys=True))


def cmd_apps(_):
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                               "configs", "nuxel", "app-registry", "app_registry.json")) as fh:
            reg = json.load(fh)
    except (OSError, ValueError):
        reg = {}
    for app in reg.get("apps", []):
        print("%-24s %-10s %-10s classid=%s" % (
            app.get("app_id", "?"), app.get("type", "?"),
            app.get("network_class", "?"), app.get("cgroup_classid", "-")))


def cmd_rules(_):
    policy = _load_policy()
    for sid, svc in (policy.get("services") or {}).items():
        print("%-24s %s/%s active=%s src=%s" % (
            sid, svc.get("protocol", "tcp"), svc.get("port", "?"),
            svc.get("active"), ",".join(svc.get("source_cidrs", []))))


def cmd_dry_run(_):
    policy = _load_policy()
    backend, probe, _ = _manager(policy)
    facts = _facts()
    policy = dict(policy)
    policy["services"] = facts["services"]
    report = FirewallManager(backend, probe=probe).dry_run(policy, facts)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


def cmd_apply(args):
    policy = _load_policy()
    backend, probe, _ = _manager(policy)
    facts = _facts()
    policy = dict(policy)
    policy["services"] = facts["services"]
    mgr = FirewallManager(backend, probe=probe)
    result = mgr.apply(policy, facts, rollback_after=args.rollback_after,
                       require_confirm=args.require_confirm)
    print(json.dumps(result, indent=2, sort_keys=True))


def cmd_confirm(_):
    backend, probe, _ = _manager()
    print(json.dumps(FirewallManager(backend, probe=probe).confirm(), indent=2))


def cmd_rollback(args):
    backend, probe, _ = _manager()
    print(json.dumps(FirewallManager(backend, probe=probe).rollback(args.tx), indent=2))


def cmd_profile(args):
    policy = _load_policy()
    if args.action == "list":
        for pid in sorted(policymod.builtin_profiles()):
            print(pid)
        return
    if args.action == "activate":
        new_policy = policymod.apply_profile(policy, args.profile_id)
        _save_policy(new_policy)
        print("activated %s" % args.profile_id)
        return
    raise SystemExit("profile requires list|activate")


def cmd_evidence(_):
    backend, probe, _ = _manager()
    print(json.dumps(backend.readback(), indent=2, sort_keys=True))


def cmd_self_test(_):
    """Offline self-test: validate schema + a dry-run render with no mutation."""
    policy = schema.validate_policy(dict(schema.DEFAULT_POLICY))
    assert policy["defaults"] == {"input": "deny", "forward": "deny",
                                  "output": "allow", "ipv4": True, "ipv6": True}
    # A render against a fake probe must produce a non-empty plan.
    probe = {
        "kernel_release": "test", "nftables_kernel": False, "iptables_kernel": True,
        "ip6tables_kernel": True, "owner_match": False, "cgroup_match": False,
        "net_cls": False,
        "binaries": {"nft": None, "iptables": "iptables", "ip6tables": "ip6tables",
                     "firewalld": None, "ufw": None},
        "backends": {"nftables": False, "iptables": True, "iptables_ipv6": True},
        "active_managers": {"firewalld": False, "ufw": False},
        "cgroup": {"unified": True, "controllers": []},
        "per_app": {"uid_owner": False, "cgroup": False, "supported": False},
    }
    backend = get_backend("iptables", probe)
    plan = backend.render(policy, {"services": {}, "app_uids": {}})
    assert plan["ipv4"], "ipv4 plan empty"
    print("self-test: OK")


def build_parser():
    p = argparse.ArgumentParser(prog="nuxel-firewall")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("backend-probe").set_defaults(func=cmd_backend_probe)
    sub.add_parser("apps").set_defaults(func=cmd_apps)
    sub.add_parser("rules").set_defaults(func=cmd_rules)
    sub.add_parser("dry-run").set_defaults(func=cmd_dry_run)

    a = sub.add_parser("apply")
    a.add_argument("--rollback-after", type=int, default=60)
    a.add_argument("--no-confirm", dest="require_confirm", action="store_false")
    a.set_defaults(require_confirm=True, func=cmd_apply)

    sub.add_parser("confirm").set_defaults(func=cmd_confirm)
    r = sub.add_parser("rollback")
    r.add_argument("--tx")
    r.set_defaults(func=cmd_rollback)

    pr = sub.add_parser("profile")
    pr.add_argument("action", choices=["list", "activate"])
    pr.add_argument("profile_id", nargs="?")
    pr.set_defaults(func=cmd_profile)

    sub.add_parser("evidence").set_defaults(func=cmd_evidence)
    sub.add_parser("self-test").set_defaults(func=cmd_self_test)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
        return 0
    except (TransactionError, UnsupportedError, schema.PolicyValidationError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
