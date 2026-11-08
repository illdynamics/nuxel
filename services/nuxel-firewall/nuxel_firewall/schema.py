"""Canonical policy schema + validation (one versioned model for every consumer).

A rule that cannot be expressed here cannot be applied: the UI, daemon, CLI,
backend compilers and profile manager all consume this exact model.
"""
import ipaddress
import re

SCHEMA_VERSION = 1

DIRECTIONS = ("input", "output", "forward")
ACTIONS = ("allow", "deny")
PROTOCOLS = ("tcp", "udp", "icmp", "icmpv6", "sctp", "any")
SERVICE_TRANSPORTS = ("tcp", "udp")

CIDR_RE = re.compile(r"^[0-9a-fA-F:./]+$")
PORT_RE = re.compile(r"^\d{1,5}$")
APP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

DEFAULT_POLICY = {
    "schema_version": SCHEMA_VERSION,
    "enabled": False,
    "backend": "auto",
    "defaults": {
        "input": "deny",
        "forward": "deny",
        "output": "allow",
        "ipv4": True,
        "ipv6": True,
    },
    "app_defaults": {
        "outbound": "inherit_global",
        "new_app_policy": "inherit",
    },
    "services": {},
    "apps": {},
    "networks": {},
    "logging": {
        "blocked_log": False,
        "rate": "10/minute",
    },
    "safety": {
        "rollback_seconds": 60,
        "require_confirm": True,
    },
    "profiles": {},
}


class PolicyValidationError(ValueError):
    pass


def _fail(msg):
    raise PolicyValidationError(msg)


def validate_ip(value, family=None):
    """Return a canonical string for a single IP or a CIDR, else raise."""
    if not isinstance(value, str) or not CIDR_RE.match(value):
        _fail("invalid address %r" % (value,))
    try:
        obj = ipaddress.ip_network(value, strict=False)
    except ValueError:
        _fail("invalid CIDR %r" % (value,))
    if "/" not in value:
        obj = ipaddress.ip_interface(value).network
    if family == 4 and obj.version != 4:
        _fail("expected IPv4, got %r" % (value,))
    if family == 6 and obj.version != 6:
        _fail("expected IPv6, got %r" % (value,))
    return str(obj)


def validate_port(value, name="port"):
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 65535:
        return value
    if isinstance(value, str) and PORT_RE.match(value) and 0 <= int(value) <= 65535:
        return int(value)
    _fail("invalid %s %r" % (name, value))


def validate_port_range(value):
    if isinstance(value, dict):
        if sorted(value.keys()) != ["from", "to"]:
            _fail("port range needs exactly 'from' and 'to'")
        lo = validate_port(value["from"], "port.from")
        hi = validate_port(value["to"], "port.to")
        if lo > hi:
            _fail("port range from %d > to %d" % (lo, hi))
        return (lo, hi)
    return validate_port(value)


def _reject_unknown(obj, allowed, where):
    if not isinstance(obj, dict):
        _fail("%s must be an object" % where)
    for key in obj:
        if key not in allowed:
            _fail("unknown key %r in %s" % (key, where))


def validate_app_id(app_id):
    if not isinstance(app_id, str) or not APP_ID_RE.match(app_id):
        _fail("invalid app id %r" % (app_id,))
    return app_id


def _validate_service_rule(service_id, rule):
    _reject_unknown(
        rule,
        {"protocol", "port", "bind_addresses", "interfaces", "source_cidrs",
         "enabled", "active", "security_note", "id"},
        "services.%s" % service_id,
    )
    proto = rule.get("protocol", "tcp")
    if proto not in SERVICE_TRANSPORTS:
        _fail("service %s protocol must be tcp/udp, got %r" % (service_id, proto))
    if "port" not in rule:
        _fail("service %s missing port" % service_id)
    ports = validate_port_range(rule["port"])
    for fam in ("bind_addresses", "source_cidrs", "interfaces"):
        value = rule.get(fam, [])
        if not isinstance(value, list):
            _fail("service %s %s must be a list" % (service_id, fam))
        for entry in value:
            if not isinstance(entry, str):
                _fail("service %s %s entries must be strings" % (service_id, fam))
            if fam in ("bind_addresses", "source_cidrs"):
                validate_ip(entry)
    return {
        "id": service_id,
        "protocol": proto,
        "port": ports,
        "bind_addresses": list(rule.get("bind_addresses", [])),
        "interfaces": list(rule.get("interfaces", [])),
        "source_cidrs": list(rule.get("source_cidrs", [])),
        "enabled": bool(rule.get("enabled", False)),
        "active": bool(rule.get("active", False)),
        "security_note": rule.get("security_note", ""),
    }


def validate_policy(policy):
    """Validate and return a normalized deep copy, or raise PolicyValidationError."""
    if not isinstance(policy, dict):
        _fail("policy must be an object")
    if policy.get("schema_version") != SCHEMA_VERSION:
        _fail("unsupported schema_version %r" % (policy.get("schema_version"),))

    _reject_unknown(
        policy,
        {"schema_version", "enabled", "backend", "defaults", "app_defaults",
         "services", "apps", "networks", "logging", "safety", "profiles"},
        "policy",
    )

    backend = policy.get("backend", "auto")
    if backend not in ("auto", "iptables", "nftables", "firewalld", "ufw"):
        _fail("invalid backend %r" % (backend,))

    defaults = policy.get("defaults", {})
    _reject_unknown(defaults, {"input", "forward", "output", "ipv4", "ipv6"}, "defaults")
    for d in DIRECTIONS:
        if defaults.get(d) not in ACTIONS:
            _fail("defaults.%s must be allow|deny, got %r" % (d, defaults.get(d)))
    for fam in ("ipv4", "ipv6"):
        if not isinstance(defaults.get(fam, True), bool):
            _fail("defaults.%s must be boolean" % fam)

    app_defaults = policy.get("app_defaults", {})
    _reject_unknown(app_defaults, {"outbound", "new_app_policy"}, "app_defaults")
    if app_defaults.get("outbound", "inherit_global") not in ("inherit_global", "allow", "deny"):
        _fail("app_defaults.outbound invalid")
    if app_defaults.get("new_app_policy", "inherit") not in ("inherit", "allow", "deny"):
        _fail("app_defaults.new_app_policy invalid")

    services = {}
    for sid, rule in (policy.get("services") or {}).items():
        services[sid] = _validate_service_rule(sid, rule)

    apps = {}
    seen_apps = {}
    for app_id, override in (policy.get("apps") or {}).items():
        validate_app_id(app_id)
        key = app_id.lower()
        if key in seen_apps:
            _fail("duplicate app id %r (collides with %r)" % (app_id, seen_apps[key]))
        seen_apps[key] = app_id
        _reject_unknown(override, {"outbound", "networks", "category"}, "apps.%s" % app_id)
        outbound = override.get("outbound", "inherit")
        if outbound not in ("inherit", "allow", "deny"):
            _fail("apps.%s.outbound invalid" % app_id)
        networks = override.get("networks", {})
        if not isinstance(networks, dict):
            _fail("apps.%s.networks must be an object" % app_id)
        for net, val in networks.items():
            if val not in ("inherit", "allow", "deny"):
                _fail("apps.%s.networks.%s invalid" % (app_id, net))
        apps[app_id] = {
            "outbound": outbound,
            "networks": dict(networks),
            "category": override.get("category", ""),
        }

    networks = policy.get("networks", {})
    if not isinstance(networks, dict):
        _fail("networks must be an object")
    for net, entry in networks.items():
        if not isinstance(entry, dict):
            _fail("networks.%s must be an object" % net)
        _reject_unknown(entry, {"interfaces", "cidrs", "trust"}, "networks.%s" % net)
        for cidr in entry.get("cidrs", []) or []:
            validate_ip(cidr)

    logging = policy.get("logging", {})
    _reject_unknown(logging, {"blocked_log", "rate"}, "logging")
    if not isinstance(logging.get("blocked_log", False), bool):
        _fail("logging.blocked_log must be boolean")

    safety = policy.get("safety", {})
    _reject_unknown(safety, {"rollback_seconds", "require_confirm"}, "safety")
    rollback = safety.get("rollback_seconds", 60)
    if not isinstance(rollback, int) or isinstance(rollback, bool) or not (10 <= rollback <= 600):
        _fail("safety.rollback_seconds must be an integer 10..600")
    if not isinstance(safety.get("require_confirm", True), bool):
        _fail("safety.require_confirm must be boolean")

    profiles = policy.get("profiles", {})
    if not isinstance(profiles, dict):
        _fail("profiles must be an object")
    for pid, prof in profiles.items():
        if not isinstance(prof, dict):
            _fail("profiles.%s must be an object" % pid)

    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": bool(policy.get("enabled", False)),
        "backend": backend,
        "defaults": {
            "input": defaults.get("input", "deny"),
            "forward": defaults.get("forward", "deny"),
            "output": defaults.get("output", "allow"),
            "ipv4": bool(defaults.get("ipv4", True)),
            "ipv6": bool(defaults.get("ipv6", True)),
        },
        "app_defaults": {
            "outbound": app_defaults.get("outbound", "inherit_global"),
            "new_app_policy": app_defaults.get("new_app_policy", "inherit"),
        },
        "services": services,
        "apps": apps,
        "networks": dict(networks),
        "logging": {"blocked_log": logging.get("blocked_log", False), "rate": logging.get("rate", "10/minute")},
        "safety": {"rollback_seconds": rollback, "require_confirm": safety.get("require_confirm", True)},
        "profiles": dict(profiles),
    }
