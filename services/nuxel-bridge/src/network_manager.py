#!/usr/bin/env python3
"""Nuxel Network Manager provider: private DNS, VPN and ZeroTier.

The HTTP bridge already owns the live NetworkManager Wi-Fi connector.  This
module is the *same* owner surface for the extra controls requested by the
Network Manager wrapper app.  It never accepts a shell string: every external
command is a fixed argv list, every caller-supplied identifier is validated,
and command output is reported truthfully (a missing plugin is an explicit
capability result, never a fake success).

The module is deliberately standard-library only so unit tests can import it
without D-Bus, GTK or root.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ZEROTIER_ID_RE = re.compile(r"^[0-9a-f]{16}$")
VPN_KINDS = ("wireguard", "openvpn")
MAX_CONFIG_BYTES = 1024 * 1024
STATE_DIR = Path("/etc/nuxel/network")

DNS_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "cloudflare": {
        "label": "Cloudflare",
        "ipv4": ["1.1.1.1", "1.0.0.1"],
        "ipv6": ["2606:4700:4700::1111", "2606:4700:4700::1001"],
        "dot_name": "1dot1dot1dot1.cloudflare-dns.com",
    },
    "quad9": {
        "label": "Quad9",
        "ipv4": ["9.9.9.9", "149.112.112.112"],
        "ipv6": ["2620:fe::fe", "2620:fe::9"],
        "dot_name": "dns.quad9.net",
    },
    "dhcp": {"label": "Automatic (DHCP)", "ipv4": [], "ipv6": [], "dot_name": ""},
    "custom": {"label": "Custom", "ipv4": [], "ipv6": [], "dot_name": ""},
}


class NetworkManagerError(Exception):
    """A validated, user-presentable network action error."""

    def __init__(self, message: str, code: str = "NETWORK_MANAGER_ERROR"):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Validation helpers (unit-tested without a live NetworkManager)
# ---------------------------------------------------------------------------

def split_nmcli_terse(line: str) -> List[str]:
    """Split nmcli terse output on unescaped ':' characters."""
    fields: List[str] = []
    current: List[str] = []
    escaped = False
    for char in line.rstrip("\n"):
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return fields


def valid_zerotier_id(value: Any) -> bool:
    return bool(ZEROTIER_ID_RE.match(str(value or "").strip().lower()))


def normalize_dns_servers(values: Any) -> Tuple[List[str], List[str]]:
    """Return validated (ipv4, ipv6) server strings, preserving order."""
    if isinstance(values, str):
        values = re.split(r"[\s,]+", values.strip())
    if not isinstance(values, (list, tuple)):
        raise NetworkManagerError("DNS servers must be a list", "INVALID_DNS")
    ipv4: List[str] = []
    ipv6: List[str] = []
    for raw in values:
        text = str(raw or "").strip()
        if not text:
            continue
        try:
            address = ipaddress.ip_address(text)
        except ValueError as exc:
            raise NetworkManagerError("invalid DNS server: %s" % text, "INVALID_DNS") from exc
        target = ipv4 if address.version == 4 else ipv6
        if str(address) not in target:
            target.append(str(address))
    if len(ipv4) > 8 or len(ipv6) > 8:
        raise NetworkManagerError("too many DNS servers", "INVALID_DNS")
    return ipv4, ipv6


def dns_servers_for(provider: Any, custom: Any = None) -> Tuple[str, List[str], List[str]]:
    key = str(provider or "").strip().lower()
    if key not in DNS_PROVIDERS:
        raise NetworkManagerError("unknown DNS provider", "INVALID_DNS_PROVIDER")
    if key in ("cloudflare", "quad9"):
        spec = DNS_PROVIDERS[key]
        return key, list(spec["ipv4"]), list(spec["ipv6"])
    if key == "dhcp":
        return key, [], []
    ipv4, ipv6 = normalize_dns_servers(custom)
    if not ipv4 and not ipv6:
        raise NetworkManagerError("custom DNS needs at least one server", "INVALID_DNS")
    return "custom", ipv4, ipv6


def validate_vpn_config(kind: Any, text: Any) -> str:
    """Validate an imported WireGuard/OpenVPN profile without logging secrets."""
    key = str(kind or "").strip().lower()
    if key not in VPN_KINDS:
        raise NetworkManagerError("VPN type must be wireguard or openvpn", "INVALID_VPN_KIND")
    config = str(text or "")
    if not config.strip():
        raise NetworkManagerError("VPN configuration is empty", "INVALID_VPN_CONFIG")
    if len(config.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise NetworkManagerError("VPN configuration is too large", "VPN_CONFIG_TOO_LARGE")
    if "\x00" in config:
        raise NetworkManagerError("VPN configuration contains NUL", "INVALID_VPN_CONFIG")
    if key == "wireguard":
        if "[Interface]" not in config or "PrivateKey" not in config:
            raise NetworkManagerError("WireGuard config needs [Interface] and PrivateKey",
                                      "INVALID_VPN_CONFIG")
    else:
        low = config.lower()
        if "remote " not in low or ("client" not in low and "dev tun" not in low):
            raise NetworkManagerError("OpenVPN config needs client/dev tun and remote",
                                      "INVALID_VPN_CONFIG")
    return config


# ---------------------------------------------------------------------------
# Bounded command execution
# ---------------------------------------------------------------------------

def _run(argv: Sequence[str], timeout: float = 25.0,
         input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(list(argv), capture_output=True, text=True,
                              timeout=timeout, input=input_text,
                              stdin=None if input_text is not None else subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(list(argv), 124, "", "timed out after %.0fs" % timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(list(argv), 127, "", str(exc))


def _nmcli(*args: str, timeout: float = 25.0) -> subprocess.CompletedProcess:
    return _run(["nmcli", *args], timeout=timeout)


def _nmcli_success(*args: str, timeout: float = 25.0) -> subprocess.CompletedProcess:
    proc = _nmcli(*args, timeout=timeout)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[-800:]
        raise NetworkManagerError(detail or "NetworkManager refused the request",
                                  "NMCLI_FAILED")
    return proc


def connections() -> List[Dict[str, Any]]:
    """Return every NetworkManager connection with its stable UUID."""
    proc = _nmcli("-t", "-f", "UUID,NAME,TYPE,DEVICE", "connection", "show")
    if proc.returncode != 0:
        raise NetworkManagerError((proc.stderr or proc.stdout or "nmcli unavailable").strip(),
                                  "NMCLI_UNAVAILABLE")
    rows: List[Dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        fields = split_nmcli_terse(line)
        if len(fields) < 4:
            continue
        uuid, name, ctype, device = fields[:4]
        if not uuid or uuid == "--":
            continue
        rows.append({
            "uuid": uuid,
            "name": name,
            "type": ctype,
            "device": "" if device in ("--", "") else device,
            "active": bool(device and device != "--"),
        })
    return rows


def active_wifi_connection() -> Optional[Dict[str, Any]]:
    for row in connections():
        if row["type"] == "802-11-wireless" and row["device"]:
            return row
    for row in connections():
        if row["type"] == "802-11-wireless":
            return row
    return None


def _connection_value(uuid: str, key: str) -> str:
    proc = _nmcli("-g", key, "connection", "show", uuid)
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def dns_status() -> Dict[str, Any]:
    conn = active_wifi_connection()
    doc: Dict[str, Any] = {
        "success": True,
        "providers": DNS_PROVIDERS,
        "connection": conn,
        "ipv4_dns": [],
        "ipv6_dns": [],
        "ignore_auto_ipv4": False,
        "ignore_auto_ipv6": False,
        "dot_active": False,
        "dot_available": systemd_resolved_active(),
        "resolv_conf": [],
    }
    if not conn:
        doc["success"] = False
        doc["error"] = "no active Wi-Fi connection"
        doc["error_code"] = "NO_ACTIVE_WIFI"
        return doc
    uuid = conn["uuid"]
    doc["ipv4_dns"] = [x for x in re.split(r"[\s,]+", _connection_value(uuid, "ipv4.dns")) if x]
    doc["ipv6_dns"] = [x for x in re.split(r"[\s,]+", _connection_value(uuid, "ipv6.dns")) if x]
    doc["ignore_auto_ipv4"] = _connection_value(uuid, "ipv4.ignore-auto-dns").lower() == "yes"
    doc["ignore_auto_ipv6"] = _connection_value(uuid, "ipv6.ignore-auto-dns").lower() == "yes"
    try:
        with open("/etc/resolv.conf", "r", encoding="utf-8", errors="replace") as fh:
            doc["resolv_conf"] = [line.rstrip() for line in fh if line.strip()][:10]
    except OSError:
        pass
    if doc["dot_available"] and conn.get("device"):
        proc = _run(["resolvectl", "show", conn["device"]], timeout=5)
        if proc.returncode == 0:
            doc["resolvectl"] = proc.stdout[-4000:]
            doc["dot_active"] = bool(re.search(r"DNSOverTLS|\\+DNSOverTLS", proc.stdout) and
                                     "yes" in proc.stdout.lower())
    return doc


def systemd_resolved_active() -> bool:
    proc = _run(["systemctl", "is-active", "systemd-resolved"], timeout=5)
    return proc.returncode == 0 and (proc.stdout or "").strip() == "active"


def set_private_dns(provider: str, custom: Any = None) -> Dict[str, Any]:
    key, ipv4, ipv6 = dns_servers_for(provider, custom)
    conn = active_wifi_connection()
    if not conn:
        raise NetworkManagerError("no active Wi-Fi connection", "NO_ACTIVE_WIFI")
    uuid = conn["uuid"]
    if key == "dhcp":
        _nmcli_success("connection", "modify", uuid,
                       "ipv4.dns", "", "ipv4.ignore-auto-dns", "no",
                       "ipv6.dns", "", "ipv6.ignore-auto-dns", "no")
    else:
        _nmcli_success("connection", "modify", uuid,
                       "ipv4.dns", " ".join(ipv4),
                       "ipv4.ignore-auto-dns", "yes",
                       "ipv6.dns", " ".join(ipv6),
                       "ipv6.ignore-auto-dns", "yes")
    applied = False
    if conn.get("device"):
        proc = _nmcli("device", "reapply", conn["device"], timeout=30)
        applied = proc.returncode == 0
        if not applied:
            # Re-activating would drop the owner's SSH session; report that the
            # profile is saved but live application needs a reconnect.
            pass
    dot_active = False
    if key != "dhcp" and systemd_resolved_active() and conn.get("device"):
        if ipv4 or ipv6:
            _run(["resolvectl", "dns", conn["device"], *ipv4, *ipv6], timeout=10)
        _run(["resolvectl", "dnsovertls", conn["device"], "yes"], timeout=10)
        _run(["resolvectl", "domain", conn["device"], "~."], timeout=10)
        check = _run(["resolvectl", "show", conn["device"]], timeout=5)
        dot_active = check.returncode == 0 and "+DNSOverTLS" in check.stdout
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state = {"schema_version": 1, "provider": key, "ipv4": ipv4, "ipv6": ipv6,
                 "updated_at": time.time()}
        tmp = STATE_DIR / ("private-dns.%d.tmp" % os.getpid())
        tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        os.chmod(tmp, 0o644)
        os.replace(tmp, STATE_DIR / "private-dns.json")
    except OSError:
        pass
    doc = dns_status()
    doc.update({"applied": applied, "dot_active": dot_active, "provider": key,
                "saved_ipv4": ipv4, "saved_ipv6": ipv6})
    return doc


def reset_private_dns() -> Dict[str, Any]:
    return set_private_dns("dhcp")


# ---------------------------------------------------------------------------
# VPN
# ---------------------------------------------------------------------------

def _vpn_connections(rows: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    rows = rows if rows is not None else connections()
    return [row for row in rows if row["type"] in ("vpn", "wireguard") or
            row["type"].startswith("vpn-")]


def vpn_status() -> Dict[str, Any]:
    rows = connections()
    vpns = _vpn_connections(rows)
    plugins = {
        "openvpn": bool(shutil.which("openvpn")),
        "wireguard": bool(shutil.which("wg")),
        "nm_openvpn": bool(shutil.which("nmcli")) and _nm_vpn_plugin_present("openvpn"),
    }
    return {"success": True, "connections": vpns, "plugins": plugins,
            "active_count": sum(1 for row in vpns if row.get("active")),
            "total_count": len(vpns)}


def _nm_vpn_plugin_present(kind: str) -> bool:
    """Check the installed plugin metadata, not a guessed library directory."""
    candidates = [
        Path("/usr/lib/NetworkManager/VPN/nm-%s-service.name" % kind),
        Path("/usr/lib64/NetworkManager/VPN/nm-%s-service.name" % kind),
        Path("/usr/lib64/NetworkManager/libnm-vpn-plugin-%s.so" % kind),
        Path("/usr/lib/NetworkManager/libnm-vpn-plugin-%s.so" % kind),
    ]
    if any(path.is_file() for path in candidates):
        return True
    for base in (Path("/usr/lib64/NetworkManager"), Path("/usr/lib/NetworkManager")):
        if not base.is_dir():
            continue
        try:
            if any(base.glob("libnm-vpn-plugin-%s*" % kind)):
                return True
        except OSError:
            pass
    return False


def import_vpn(kind: str, config: str, name: str = "") -> Dict[str, Any]:
    key = str(kind or "").strip().lower()
    text = validate_vpn_config(key, config)
    before = {row["uuid"] for row in connections()}
    suffix = ".conf" if key == "wireguard" else ".ovpn"
    fd, path = tempfile.mkstemp(prefix="nuxel-vpn-", suffix=suffix, dir="/run")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(path, 0o600)
        proc = _nmcli_success("connection", "import", "type", key, "file", path,
                              timeout=45)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    rows = connections()
    new_rows = [row for row in rows if row["uuid"] not in before]
    imported = new_rows[0] if new_rows else None
    safe_name = re.sub(r"[^A-Za-z0-9 ._()@+-]", "", str(name or ""))[:80].strip()
    if imported and safe_name:
        try:
            _nmcli_success("connection", "modify", imported["uuid"],
                           "connection.id", safe_name)
            imported = next((row for row in connections()
                             if row["uuid"] == imported["uuid"]), imported)
        except NetworkManagerError:
            pass
    return {"success": bool(imported), "imported": imported,
            "detail": (proc.stdout or proc.stderr or "").strip()[-800:],
            "vpn": vpn_status()}


def _vpn_uuid(value: Any) -> str:
    uuid = str(value or "").strip()
    if not re.match(r"^[0-9a-fA-F-]{8,64}$", uuid):
        raise NetworkManagerError("invalid VPN connection id", "INVALID_VPN_UUID")
    if not any(row["uuid"] == uuid for row in _vpn_connections()):
        raise NetworkManagerError("not a known VPN connection", "UNKNOWN_VPN")
    return uuid


def vpn_up(uuid: Any) -> Dict[str, Any]:
    target = _vpn_uuid(uuid)
    proc = _nmcli_success("connection", "up", "uuid", target, timeout=60)
    return {"success": True, "uuid": target,
            "detail": (proc.stdout or proc.stderr or "").strip()[-1200:],
            "vpn": vpn_status()}


def vpn_down(uuid: Any) -> Dict[str, Any]:
    target = _vpn_uuid(uuid)
    proc = _nmcli_success("connection", "down", "uuid", target, timeout=45)
    return {"success": True, "uuid": target,
            "detail": (proc.stdout or proc.stderr or "").strip()[-1200:],
            "vpn": vpn_status()}


def vpn_delete(uuid: Any) -> Dict[str, Any]:
    target = _vpn_uuid(uuid)
    _nmcli_success("connection", "delete", "uuid", target, timeout=30)
    return {"success": True, "uuid": target, "vpn": vpn_status()}


# ---------------------------------------------------------------------------
# ZeroTier
# ---------------------------------------------------------------------------

def _zerotier_cli() -> Optional[str]:
    for candidate in ("/usr/sbin/zerotier-cli", "/usr/bin/zerotier-cli"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("zerotier-cli")


def _zt_json(*args: str) -> Any:
    exe = _zerotier_cli()
    if not exe:
        raise NetworkManagerError("zerotier-cli is not installed", "ZEROTIER_MISSING")
    proc = _run([exe, "-j", *args], timeout=15)
    if proc.returncode != 0:
        raise NetworkManagerError((proc.stderr or proc.stdout or "zerotier-cli failed").strip(),
                                  "ZEROTIER_FAILED")
    text = (proc.stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError as exc:
        raise NetworkManagerError("zerotier-cli returned invalid JSON", "ZEROTIER_BAD_JSON") from exc


def _zt_text(*args: str) -> Dict[str, Any]:
    exe = _zerotier_cli()
    if not exe:
        raise NetworkManagerError("zerotier-cli is not installed", "ZEROTIER_MISSING")
    proc = _run([exe, *args], timeout=15)
    return {"success": proc.returncode == 0, "rc": proc.returncode,
            "stdout": (proc.stdout or "").strip()[-4000:],
            "stderr": (proc.stderr or "").strip()[-4000:]}


def zerotier_status() -> Dict[str, Any]:
    exe = _zerotier_cli()
    doc: Dict[str, Any] = {
        "success": True,
        "installed": bool(exe),
        "binary": exe or "",
        "service_active": _run(["systemctl", "is-active", "zerotier-one"],
                               timeout=5).stdout.strip() == "active",
        "address": "", "online": None, "version": "", "networks": [],
    }
    if not exe:
        doc["success"] = False
        doc["error"] = "zerotier-one is not installed"
        doc["error_code"] = "ZEROTIER_MISSING"
        return doc
    try:
        info = _zt_json("info") or {}
        if isinstance(info, dict):
            doc["address"] = str(info.get("address") or "")
            doc["online"] = info.get("online")
            doc["version"] = str(info.get("version") or "")
    except NetworkManagerError as exc:
        doc["info_error"] = str(exc)
    try:
        nets = _zt_json("listnetworks") or []
        if isinstance(nets, dict):
            nets = [nets]
        doc["networks"] = nets if isinstance(nets, list) else []
    except NetworkManagerError as exc:
        doc["networks_error"] = str(exc)
    return doc


def zerotier_join(network_id: Any) -> Dict[str, Any]:
    nwid = str(network_id or "").strip().lower()
    if not valid_zerotier_id(nwid):
        raise NetworkManagerError("ZeroTier network id must be 16 hex characters",
                                  "INVALID_ZEROTIER_ID")
    result = _zt_text("join", nwid)
    if not result["success"]:
        raise NetworkManagerError(result["stderr"] or result["stdout"], "ZEROTIER_JOIN_FAILED")
    return {"success": True, "network_id": nwid, "detail": result["stdout"],
            "zerotier": zerotier_status()}


def zerotier_leave(network_id: Any) -> Dict[str, Any]:
    nwid = str(network_id or "").strip().lower()
    if not valid_zerotier_id(nwid):
        raise NetworkManagerError("ZeroTier network id must be 16 hex characters",
                                  "INVALID_ZEROTIER_ID")
    result = _zt_text("leave", nwid)
    if not result["success"]:
        raise NetworkManagerError(result["stderr"] or result["stdout"], "ZEROTIER_LEAVE_FAILED")
    return {"success": True, "network_id": nwid, "detail": result["stdout"],
            "zerotier": zerotier_status()}


def zerotier_set_enabled(enabled: bool) -> Dict[str, Any]:
    action = "start" if enabled else "stop"
    proc = _run(["systemctl", action, "zerotier-one"], timeout=30)
    if proc.returncode != 0:
        raise NetworkManagerError((proc.stderr or proc.stdout or "systemctl failed").strip(),
                                  "ZEROTIER_SERVICE_FAILED")
    return {"success": True, "enabled": bool(enabled), "zerotier": zerotier_status()}


# ---------------------------------------------------------------------------
# Dispatcher used by the HTTP bridge
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Native hotspot: the service owns wlan1; NM retains wlan0. Sharing uses
# explicit cellular policy routing and the same upstream state as USB.
HOTSPOT_TOOL = "/usr/libexec/nuxel/nuxel-hotspot"
HOTSPOT_STATE = "/run/nuxel-hotspot/state.json"


def _hotspot_tool() -> str:
    if os.path.exists(HOTSPOT_TOOL):
        return HOTSPOT_TOOL
    return shutil.which("nuxel-hotspot") or ""


def _wifi_ap_capability() -> Dict[str, Any]:
    """Prove AP mode from nl80211 itself (never from a product description)."""
    tool = _hotspot_tool()
    if not tool:
        return {"supported": False, "reason": "nuxel-hotspot helper is not installed"}
    iw = _run(["/usr/sbin/iw", "list"], timeout=8)
    if iw.returncode != 0:
        return {"supported": False, "reason": "iw/nl80211 unavailable; cannot prove AP mode"}
    text = iw.stdout or ""
    if "valid interface combinations" not in text or "AP" not in text:
        return {"supported": False, "reason": "nl80211 reports no AP mode"}
    if not shutil.which("hostapd"):
        return {"supported": False, "reason": "hostapd is not installed"}
    if not shutil.which("dnsmasq"):
        return {"supported": False, "reason": "dnsmasq is not installed"}
    return {"supported": True, "reason": None}


HOTSPOT_CONFIG = Path('/var/lib/nuxel/hotspot/config.json')


def _hotspot_config(ssid='', password='', band=''):
    import secrets
    try:
        saved = json.loads(HOTSPOT_CONFIG.read_text())
    except FileNotFoundError:
        saved = {'ssid': 'Nuxel', 'password': secrets.token_urlsafe(18), 'band': '2.4'}
    if ssid: saved['ssid'] = ssid
    if password: saved['password'] = password
    if band: saved['band'] = band
    if not re.fullmatch(r'[ -~]{1,32}', saved['ssid']) or not re.fullmatch(r'[ -~]{8,63}', saved['password']):
        raise NetworkManagerError('SSID or WPA2 password has invalid length or characters')
    if saved['band'] not in ('2.4', '5'):
        raise NetworkManagerError('Unsupported hotspot band')
    HOTSPOT_CONFIG.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix='.config-', dir=HOTSPOT_CONFIG.parent)
    with os.fdopen(fd, 'w') as f:
        json.dump(saved, f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, HOTSPOT_CONFIG)
    return saved


def hotspot_status() -> Dict[str, Any]:
    tool = _hotspot_tool()
    if not tool: return {'success': True, 'supported': False, 'enabled': False, 'state': 'unavailable'}
    proc = _run([tool, 'status'], timeout=10)
    try: st = json.loads(proc.stdout)
    except ValueError: return {'success': False, 'error': 'Hotspot status unavailable'}
    st['success'] = proc.returncode == 0
    try:
        config = json.loads(HOTSPOT_CONFIG.read_text())
        st['ssid'] = config['ssid']; st['band'] = config['band']
    except (OSError, ValueError): pass
    return st


def hotspot_start(ssid: str = '', password: str = '', band: str = '') -> Dict[str, Any]:
    try:
        _hotspot_config(ssid, password, band)
        proc = _run(['systemctl', 'restart', 'nuxel-hotspot.service'], timeout=45)
        if proc.returncode: return {'success': False, 'error': proc.stderr.strip() or 'Hotspot service refused'}
        import time
        for _ in range(30):
            st = hotspot_status()
            if st.get('enabled'): return st
            if _run(['systemctl','is-active','--quiet','nuxel-hotspot.service']).returncode: break
            time.sleep(.3)
        return {'success': False, 'error': st.get('last_error') or 'Access point did not start; inspect hotspot service error'}
    except (OSError, ValueError, NetworkManagerError) as exc:
        return {'success': False, 'error': str(exc)}


def hotspot_stop() -> Dict[str, Any]:
    proc = _run(['systemctl', 'stop', 'nuxel-hotspot.service'], timeout=25)
    st = hotspot_status(); st['success'] = proc.returncode == 0 and not st.get('enabled')
    return st


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params if isinstance(params, dict) else {}
    verb = str(verb or "")
    if verb in ("dns-status", "dns"):
        return dns_status()
    if verb == "dns-set":
        return set_private_dns(str(params.get("provider") or ""), params.get("servers"))
    if verb == "dns-reset":
        return reset_private_dns()
    if verb == "vpn-status":
        return vpn_status()
    if verb == "vpn-import":
        return import_vpn(str(params.get("kind") or ""),
                          str(params.get("config") or ""),
                          str(params.get("name") or ""))
    if verb == "vpn-up":
        return vpn_up(params.get("uuid"))
    if verb == "vpn-down":
        return vpn_down(params.get("uuid"))
    if verb == "vpn-delete":
        return vpn_delete(params.get("uuid"))
    if verb == "zerotier-status":
        return zerotier_status()
    if verb == "zerotier-join":
        return zerotier_join(params.get("network_id"))
    if verb == "zerotier-leave":
        return zerotier_leave(params.get("network_id"))
    if verb == "zerotier-enabled":
        return zerotier_set_enabled(bool(params.get("enabled")))
    if verb == "hotspot-status":
        return hotspot_status()
    if verb == "hotspot-start":
        return hotspot_start(str(params.get("ssid") or ""),
                             str(params.get("password") or ""), str(params.get("band") or ""))
    if verb == "hotspot-stop":
        return hotspot_stop()
    raise NetworkManagerError("unknown network-manager verb: " + verb, "UNKNOWN_VERB")
