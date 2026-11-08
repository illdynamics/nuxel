"""Remote-access discovery: SSH/XRDP/VNC listeners, sshd config, live sessions.

These facts are read fresh before any policy is generated or applied.  Nothing
here edits sshd/XRDP/VNC/NetworkManager configuration.
"""
import re
import subprocess


def _run(argv, timeout=6):
    try:
        return subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def sshd_effective():
    """Parse `sshd -T` (key-value) into a dict."""
    r = _run(["sshd", "-T"])
    if not r or r.returncode != 0:
        return {}
    out = {}
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line or " " not in line:
            continue
        key, _, value = line.partition(" ")
        if key not in out:
            out[key] = value
        else:
            if not isinstance(out[key], list):
                out[key] = [out[key]]
            out[key].append(value)
    return out


def listening_sockets():
    """Return list of dicts for TCP/UDP listeners via `ss -lntup`."""
    r = _run(["ss", "-lntup"])
    if not r or r.returncode != 0:
        return []
    listeners = []
    # Lines look like: LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=1,fd=3))
    for line in r.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 5 or parts[0] != "LISTEN":
            continue
        addr = parts[3]
        proto = parts[0].lower()
        host, _, port = addr.rpartition(":")
        if not port.isdigit():
            continue
        proc = ""
        m = re.search(r"users:\(\\(\"([^\"]+)\"", line)
        if m:
            proc = m.group(1)
        listeners.append({
            "protocol": proto,
            "address": host,
            "port": int(port),
            "process": proc,
        })
    return listeners


def established_ssh_sessions():
    """Established TCP sessions involving local port 22 (both directions)."""
    r = _run(["ss", "-tnp", "state", "established"])
    if not r or r.returncode != 0:
        return []
    sessions = []
    for line in r.stdout.splitlines()[1:]:
        if ":22 " not in line and " :22 " not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local, remote = parts[3], parts[4]
        local_host, _, local_port = local.rpartition(":")
        remote_host, _, remote_port = remote.rpartition(":")
        sessions.append({
            "local": local,
            "remote": remote,
            "local_host": local_host,
            "local_port": local_port,
            "remote_host": remote_host,
            "remote_port": remote_port,
        })
    return sessions


def ssh_allow_cidrs():
    """Extract source CIDRs from sshd AllowUsers (user@cidr)."""
    cfg = sshd_effective()
    users = cfg.get("allowusers", [])
    if isinstance(users, str):
        users = [users]
    cidrs = set()
    for entry in users:
        if "@" in entry:
            _, _, cidr = entry.rpartition("@")
            cidrs.add(cidr)
    return sorted(cidrs)


def ssh_ports(cfg):
    ports = cfg.get("port", [])
    if isinstance(ports, str):
        ports = [ports]
    try:
        return sorted({int(p) for p in ports})
    except (ValueError, TypeError):
        return [22]


def discover():
    """Return the complete remote-access fact sheet."""
    sshd = sshd_effective()
    listeners = listening_sockets()
    ssh_port_list = ssh_ports(sshd)
    ssh_listeners = [l for l in listeners if l["port"] in ssh_port_list]
    xrdp_listeners = [l for l in listeners if l["port"] == 3389]
    vnc_listeners = [l for l in listeners if l["port"] == 5900]
    return {
        "sshd": {
            "port": sshd.get("port", [22]),
            "listen_address": sshd.get("listenaddress", []),
            "allow_users": sshd.get("allowusers", []),
            "permit_root_login": sshd.get("permitrootlogin", ""),
            "password_auth": sshd.get("passwordauthentication", ""),
            "pubkey_auth": sshd.get("pubkeyauthentication", ""),
            "allow_tcp_forwarding": sshd.get("allowtcpforwarding", ""),
            "permit_open": sshd.get("permitopen", []),
            "allow_cidrs": ssh_allow_cidrs(),
        },
        "listeners": listeners,
        "ssh_listeners": ssh_listeners,
        "xrdp_listeners": xrdp_listeners,
        "vnc_listeners": vnc_listeners,
        "established_ssh": established_ssh_sessions(),
    }


def build_service_policies(discovered, existing_services):
    """Turn live facts into the named inbound service policies.

    SSH is prepared from the effective sshd config + actual listener.  XRDP/VNC
    are prepared but inactive unless a real listener exists.  Existing explicit
    source restrictions in the policy are preserved; never broadened.
    """
    sshd = discovered["sshd"]
    services = dict(existing_services or {})

    ssh_port_list = ssh_ports(sshd)
    ssh_rule = services.setdefault("nuxel-ssh-owner", {})
    ssh_rule.update({
        "protocol": "tcp",
        "port": ssh_port_list if len(ssh_port_list) > 1 else ssh_port_list[0],
        "source_cidrs": sshd["allow_cidrs"],
        "bind_addresses": [],
        "interfaces": _ssh_interfaces(discovered),
        "enabled": bool(discovered["ssh_listeners"]),
        "active": bool(discovered["ssh_listeners"]),
        "security_note": "key-only SSH; source-restricted by sshd AllowUsers",
    })

    xrdp = services.setdefault("nuxel-xrdp-owner-lan", {})
    if discovered["xrdp_listeners"]:
        xrdp.update({
            "protocol": "tcp", "port": 3389, "enabled": True, "active": True,
            "source_cidrs": _trusted_lan_cidrs(),
            "interfaces": ["wlan0"],
            "security_note": "XRDP TLS+PAM; trusted LAN/mesh only",
        })
    else:
        xrdp.setdefault("protocol", "tcp")
        xrdp.setdefault("port", 3389)
        xrdp["active"] = False

    vnc = services.setdefault("nuxel-vnc-owner-lan", {})
    if discovered["vnc_listeners"]:
        vnc.update({
            "protocol": "tcp", "port": 5900, "enabled": True, "active": True,
            "source_cidrs": ["127.0.0.1/32"],
            "interfaces": [],
            "security_note": "UNENCRYPTED / no VNC password auth — loopback/SSH tunnel only",
        })
    else:
        vnc.setdefault("protocol", "tcp")
        vnc.setdefault("port", 5900)
        vnc["active"] = False

    return services


def _ssh_interfaces(discovered):
    """Ingress interfaces that carry an SSH listener."""
    ifaces = set()
    for l in discovered["ssh_listeners"]:
        if l["address"] in ("0.0.0.0", "[::]", "::", "*"):
            # Wildcard bind: rely on source CIDRs, not an interface allow.
            continue
        ifaces.add(l["address"])
    return sorted(ifaces)


def _trusted_lan_cidrs():
    """Conservative default: loopback only until the owner opts into LAN/mesh."""
    return ["127.0.0.1/32"]
