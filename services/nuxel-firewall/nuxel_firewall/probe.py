"""Kernel / backend / cgroup capability probing.

Capability must be measured, never assumed from `uname -r`.  A syntax check or a
cgroup write is NOT proof of packet-level attribution.
"""
import gzip
import os
import shutil
import subprocess


def _which(*names):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def _read(path, default=""):
    try:
        with open(path, "r", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return default


def kernel_release():
    return _read("/proc/sys/kernel/osrelease", "unknown")


def _kernel_config():
    """Parse /proc/config.gz into a set of enabled CONFIG_ lines."""
    enabled = set()
    try:
        with gzip.open("/proc/config.gz", "rt", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("CONFIG_") and line.endswith("=y"):
                    enabled.add(line)
    except OSError:
        pass
    return enabled


def cgroup_layout():
    mounts = []
    for line in _read("/proc/mounts").splitlines():
        if "cgroup" in line:
            mounts.append(line)
    unified = any("cgroup2" in m for m in mounts)
    controllers = _read("/sys/fs/cgroup/cgroup.controllers")
    return {
        "unified": unified,
        "controllers": controllers.split(),
        "mounts": mounts,
    }




def _app_process_uids():
    """Sample UIDs of the processes that actually open app sockets.

    Per-app enforcement via owner-UID is only *enforceable now* if those
    socket-producing processes run under more than one distinct UID.  On the
    live handset the PWA host and WebKit network/web processes all run as root.
    """
    try:
        out = subprocess.run(
            ["ps", "-eo", "uid=,comm="], capture_output=True, text=True, timeout=6)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    names = ("nuxel-pwa-host", "WebKitNetworkProcess", "WebKitWebProcess",
             "nuxel-dialer", "nuxel-messages", "nuxel-contacts")
    uids = {}
    for line in out.stdout.splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        uid, comm = parts
        for name in names:
            if comm == name or comm.startswith(name):
                uids.setdefault(name, set()).add(uid)
    return uids

def probe():
    """Return the live capability report the UI/CLI consumes."""
    cfg = _kernel_config()
    nftables_kernel = "CONFIG_NF_TABLES=y" in cfg
    iptables_kernel = "CONFIG_IP_NF_IPTABLES=y" in cfg
    ip6tables_kernel = "CONFIG_IP6_NF_IPTABLES=y" in cfg
    owner_match = "CONFIG_NETFILTER_XT_MATCH_OWNER=y" in cfg
    cgroup_match = "CONFIG_NETFILTER_XT_MATCH_CGROUP=y" in cfg
    net_cls = "CONFIG_CGROUP_NET_CLASSID=y" in cfg

    nft_bin = _which("nft")
    iptables_bin = _which("iptables-legacy", "iptables")
    ip6tables_bin = _which("ip6tables-legacy", "ip6tables")
    firewalld = shutil.which("firewalld") or shutil.which("firewall-cmd")
    ufw = shutil.which("ufw")

    # Only a backend whose userspace + kernel feature both exist is usable.
    nftables = bool(nft_bin and nftables_kernel)
    iptables = bool(iptables_bin and iptables_kernel)
    iptables_has_v6 = bool(ip6tables_bin and ip6tables_kernel)

    # Active manager ownership (read-only).
    firewalld_active = _service_active("firewalld")
    ufw_active = _ufw_active()

    cgroup = cgroup_layout()
    per_app_uid = owner_match  # only UID owner match is a viable per-app identity
    per_app_cgroup = bool(cgroup_match and (nftables or iptables) and net_cls)

    return {
        "kernel_release": kernel_release(),
        "nftables_kernel": nftables_kernel,
        "iptables_kernel": iptables_kernel,
        "ip6tables_kernel": ip6tables_kernel,
        "owner_match": owner_match,
        "cgroup_match": cgroup_match,
        "net_cls": net_cls,
        "binaries": {
            "nft": nft_bin,
            "iptables": iptables_bin,
            "ip6tables": ip6tables_bin,
            "firewalld": firewalld,
            "ufw": ufw,
        },
        "backends": {
            "nftables": nftables,
            "iptables": iptables,
            "iptables_ipv6": iptables_has_v6,
        },
        "active_managers": {
            "firewalld": firewalld_active,
            "ufw": ufw_active,
        },
        "cgroup": cgroup,
        "per_app": {
            "uid_owner": per_app_uid,
            "cgroup": per_app_cgroup,
            "supported": per_app_cgroup or per_app_uid,
            "enforceable_now": _per_app_enforceable_now(per_app_uid, per_app_cgroup),
        },
    }




def _per_app_enforceable_now(per_app_uid, per_app_cgroup):
    """Mechanism exists AND we can currently map sockets to distinct identities.

    cgroup-based matching is only usable when the kernel exposes the cgroup
    match AND a writable net_cls/cgroup path.  UID-owner matching is only usable
    when app processes run under more than one UID.
    """
    if per_app_cgroup:
        return True
    if per_app_uid:
        uids = _app_process_uids()
        all_uids = set()
        for s in uids.values():
            all_uids |= s
        return len(all_uids) > 1
    return False


def _service_active(unit):
    try:
        out = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() == "active"
    except (OSError, subprocess.TimeoutExpired):
        return False


def _ufw_active():
    path = _which("ufw")
    if not path:
        return False
    try:
        out = subprocess.run([path, "status"], capture_output=True, text=True, timeout=5)
        return "active" in out.stdout.lower()
    except (OSError, subprocess.TimeoutExpired):
        return False


def selected_backend(policy_backend, probe_result):
    """Resolve 'auto' into the single authoritative owner, or raise on conflict."""
    managers = probe_result["active_managers"]
    if managers["firewalld"] and managers["ufw"]:
        raise RuntimeError(
            "conflict: both firewalld and ufw are active; refuse mutation")
    if policy_backend == "auto":
        if managers["firewalld"]:
            return "firewalld"
        if managers["ufw"]:
            return "ufw"
        if probe_result["backends"]["nftables"]:
            return "nftables"
        if probe_result["backends"]["iptables"]:
            return "iptables"
        return "none"
    return policy_backend
