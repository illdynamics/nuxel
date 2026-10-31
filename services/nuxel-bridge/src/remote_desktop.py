#!/usr/bin/env python3
"""Nuxel GUI remote-access provider (PWNAGE-47000).

This module is the single status/control layer for the three *graphical*
remote-access apps.  It is deliberately separate from tri_link_status.py, which
remains the read-only Serial/WLAN/USB SSH (console) truth provider.

Security boundary:
  * service, transport, port and config paths are fixed allow-lists;
  * JavaScript can never provide a command, executable, bind address or path;
  * start/stop is delegated to one fixed privileged helper with an argument
    array (no shell);
  * no password, private key or ADB secret is ever returned or logged;
  * the VNC and XRDP listeners bind to 127.0.0.1 and are reached through the
    owner's pinned-key SSH tunnel.  USB network remains BLOCKED_KERNEL_PANIC
    on the recorded 4.14.253 kernel and this module never mutates configfs.
"""

from __future__ import annotations

import base64
import fcntl
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

VERSION = "47000"
SCHEMA = "nuxel.remote-desktop-status/1"

SERVICES = ("vnc", "xrdp", "scrcpy")
TRANSPORTS = {
    "vnc": ("wlan", "usb"),
    "xrdp": ("wlan", "usb"),
    "scrcpy": ("android-adb-usb", "android-adb-tcpip"),
}
DEFAULT_TRANSPORT = {
    "vnc": "wlan",
    "xrdp": "wlan",
    "scrcpy": "android-adb-usb",
}
FIXED_PORTS = {"vnc": 5900, "xrdp": 3389}
LOOPBACK = "127.0.0.1"

KNOWN_BAD_USB_KERNELS = {"4.14.253"}
USB_PANIC_EVIDENCE = "docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/"
HELPER = os.environ.get("NUXEL_REMOTE_CTL", "/usr/local/libexec/nuxel/nuxel-remote-desktop-ctl")
STATE_DIR = Path(os.environ.get("NUXEL_REMOTE_STATE_DIR", "/run/nuxel/remote-desktop"))
PREF_FILE = Path(os.environ.get("NUXEL_REMOTE_PREF_FILE", "/var/lib/nuxel/remote-desktop/preferences.json"))
VNC_CONFIG = Path(os.environ.get("NUXEL_VNC_CONFIG", "/etc/nuxel/remote-desktop/vnc/wayvnc.conf"))
VNC_CTL = os.environ.get("NUXEL_VNC_CTL", "/usr/bin/wayvncctl")
VNC_SOCKET = os.environ.get("NUXEL_VNC_SOCKET", "/run/nuxel-wayland/wayvncctl")
VNC_SERVICE = "nuxel-remote-vnc.service"
XRDP_SERVICES = ("xrdp.service", "xrdp-sesman.service")
XRDP_CERT = Path(os.environ.get("NUXEL_XRDP_CERT", "/etc/xrdp/nuxel-cert.pem"))
XRDP_LOG = Path(os.environ.get("NUXEL_XRDP_LOG", "/var/log/xrdp.log"))
WAYLAND_RUNTIME = os.environ.get("NUXEL_WAYLAND_RUNTIME", "/run/nuxel-wayland")
WAYLAND_DISPLAY = os.environ.get("NUXEL_WAYLAND_DISPLAY", "wayland-0")


def _read(path: Path | str) -> Optional[str]:
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return None


def _run(args: Sequence[str], timeout: float = 5.0,
         env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    """Run one fixed argument vector.  Never a shell, never client input."""
    try:
        proc = subprocess.run(list(args), capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL,
                              env=env)
        return proc.returncode, (proc.stdout or ""), (proc.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _wayland_env() -> Dict[str, str]:
    env = dict(os.environ)
    env["XDG_RUNTIME_DIR"] = WAYLAND_RUNTIME
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_SESSION_TYPE"] = "wayland"
    return env


def _kernel_release() -> str:
    return _read("/proc/sys/kernel/osrelease") or ""


def _private_ipv4(addr: str) -> bool:
    try:
        a, b, *_ = [int(part) for part in addr.split(".")]
    except (ValueError, IndexError):
        return False
    return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168)


def _ipv4_from_ip_tool() -> List[Dict[str, Any]]:
    rc, out, _ = _run(["ip", "-4", "-o", "addr", "show"], timeout=3)
    if rc != 0:
        return []
    found: List[Dict[str, Any]] = []
    for line in out.splitlines():
        m = re.match(r"^\d+:\s+([^:\s@]+)(?:@\S+)?\s+inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", line)
        if m:
            found.append({"interface": m.group(1), "address": m.group(2),
                          "prefix": m.group(3)})
    return found


def _ipv4_from_ioctl() -> List[Dict[str, Any]]:
    """Fallback for images without ip(8); AF_INET ioctl, no netlink."""
    found: List[Dict[str, Any]] = []
    try:
        names = sorted(os.listdir("/sys/class/net"))
    except OSError:
        return found
    for name in names:
        if name == "lo":
            continue
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                packed = struct.pack("256s", name.encode()[:15])
                addr = socket.inet_ntoa(fcntl.ioctl(sock.fileno(), 0x8915, packed)[20:24])
                try:
                    mask = socket.inet_ntoa(fcntl.ioctl(sock.fileno(), 0x891B, packed)[20:24])
                    prefix = str(sum(bin(int(p)).count("1") for p in mask.split(".")))
                except OSError:
                    prefix = ""
            finally:
                sock.close()
            found.append({"interface": name, "address": addr, "prefix": prefix})
        except OSError:
            continue
    return found


def network_state() -> Dict[str, Any]:
    """Live IPv4 facts.  Never returns a historical hard-coded address."""
    addrs = _ipv4_from_ip_tool() or _ipv4_from_ioctl()
    usable: List[Dict[str, Any]] = []
    for item in addrs:
        name = item["interface"]
        if name.startswith(("rmnet", "lo", "docker", "veth", "br-", "p2p", "usb", "ncm", "rndis")):
            continue
        item = dict(item)
        item["private"] = _private_ipv4(item["address"])
        item["trusted_lan"] = bool(item["private"] and name.startswith("wlan"))
        usable.append(item)
    wlan = next((a for a in usable if a["interface"].startswith("wlan") and a.get("trusted_lan")), None)
    if wlan is None:
        wlan = next((a for a in usable if a.get("trusted_lan")), None)
    return {
        "interfaces": usable,
        "wlan": wlan,
        "interface": wlan["interface"] if wlan else None,
        "address": wlan["address"] if wlan else None,
        "trusted_lan": bool(wlan),
        "source": "ip -4 -o addr show" if _ipv4_from_ip_tool() else "SIOCGIFADDR",
    }


def usb_network_status(release: Optional[str] = None) -> Dict[str, Any]:
    release = release if release is not None else _kernel_release()
    gadget_root = Path("/sys/kernel/config/usb_gadget")
    functions: List[str] = []
    try:
        for gadget in gadget_root.iterdir():
            froot = gadget / "functions"
            if froot.is_dir():
                functions.extend(sorted(p.name for p in froot.iterdir()))
    except OSError:
        pass
    net_functions = [f for f in functions if f.startswith(("ncm", "ecm", "rndis"))]
    if re.sub(r"[-+].*$", "", release) in KNOWN_BAD_USB_KERNELS:
        return {
            "available": False,
            "status": "BLOCKED_KERNEL_PANIC",
            "reason": ("NCM teardown panicked this kernel (ncm_free_inst -> "
                       "misc_deregister); USB network RDP/VNC is not offered."),
            "evidence": USB_PANIC_EVIDENCE,
            "kernel_release": release,
            "gadget_functions": functions,
            "net_functions": net_functions,
            "mutated": False,
        }
    if not net_functions:
        return {
            "available": False,
            "status": "NOT_SUPPORTED_ON_DEVICE",
            "reason": "No USB network function is configured (CDC-ACM serial only).",
            "kernel_release": release,
            "gadget_functions": functions,
            "net_functions": [],
            "mutated": False,
        }
    return {
        "available": False,
        "status": "UNVERIFIED",
        "reason": "A USB network function exists but this module will not use it without a physical macOS test.",
        "kernel_release": release,
        "gadget_functions": functions,
        "net_functions": net_functions,
        "mutated": False,
    }


def _listener(port: int) -> bool:
    rc, out, _ = _run(["ss", "-ltnH"], timeout=3)
    if rc != 0:
        out = _read("/proc/net/tcp") or ""
        needle = ":%04X" % port
        return any(needle in line for line in out.splitlines()[1:])
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            local = parts[3]
            if local.endswith(":%d" % port):
                return True
    return False


def _systemctl_active(unit: str) -> bool:
    rc, out, _ = _run(["systemctl", "is-active", unit], timeout=3)
    return rc == 0 and out.strip() == "active"


def _proc_lines() -> List[str]:
    rc, out, _ = _run(["ps", "-eo", "pid,user:32,args"], timeout=3)
    return out.splitlines() if rc == 0 else []


def wayland_protocols() -> Dict[str, Any]:
    info = _which("wayland-info")
    if not info:
        return {"available": False, "protocols": [], "source": "wayland-info missing"}
    rc, out, err = _run([info], timeout=8, env=_wayland_env())
    if rc != 0:
        return {"available": False, "protocols": [], "error": (err or out).strip()[:400],
                "source": "wayland-info"}
    protocols = sorted(set(re.findall(r"interface:\s+'([^']+)'", out)))
    return {"available": True, "protocols": protocols, "source": "wayland-info"}


VNC_REQUIRED_PROTOCOLS = (
    "zwlr_screencopy_manager_v1",
    "zwlr_virtual_pointer_manager_v1",
    "zwp_virtual_keyboard_manager_v1",
)


def _vnc_clients() -> Dict[str, Any]:
    ctl = _which(VNC_CTL) or VNC_CTL
    if not os.path.exists(ctl):
        return {"count": 0, "available": False, "error": "wayvncctl missing"}
    args = [ctl, "-j"]
    if os.path.exists(VNC_SOCKET):
        args.extend(["-S", VNC_SOCKET])
    args.append("client-list")
    rc, out, err = _run(args, timeout=3, env=_wayland_env())
    if rc != 0:
        return {"count": 0, "available": False, "error": (err or out).strip()[:200]}
    try:
        doc = json.loads(out)
    except json.JSONDecodeError:
        return {"count": 0, "available": False, "error": "client-list was not JSON"}
    clients = doc.get("clients") if isinstance(doc, dict) else doc
    if not isinstance(clients, list):
        clients = []
    return {"count": len(clients), "available": True,
            "clients": [{"id": c.get("id"), "address": c.get("address"),
                         "username": c.get("username")}
                        for c in clients if isinstance(c, dict)]}


def _vnc_version() -> Optional[str]:
    exe = _which("wayvnc")
    if not exe:
        return None
    rc, out, err = _run([exe, "--version"], timeout=3)
    return (out or err).strip() or None


def _xrdp_fingerprint() -> Optional[str]:
    if not XRDP_CERT.exists():
        return None
    rc, out, _ = _run(["openssl", "x509", "-in", str(XRDP_CERT), "-noout",
                       "-fingerprint", "-sha256"], timeout=3)
    if rc != 0:
        return None
    m = re.search(r"=([0-9A-Fa-f:]+)", out)
    return m.group(1) if m else None


def _xrdp_sessions() -> Dict[str, Any]:
    lines = [line for line in _proc_lines()
             if "Xorg :" in line and "xorg-nuxel.conf" in line]
    users = sorted({line.split()[1] for line in lines if len(line.split()) > 1})
    return {"count": len(lines), "users": users, "processes": lines}


def _xrdp_last_error() -> Optional[str]:
    text = _read(XRDP_LOG)
    if not text:
        return None
    errors = [line for line in text.splitlines() if "[ERROR]" in line]
    return errors[-1][-500:] if errors else None


def _preferences() -> Dict[str, Any]:
    try:
        doc = json.loads(PREF_FILE.read_text())
        return doc if isinstance(doc, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _preferred(service: str) -> str:
    val = _preferences().get(service)
    return val if val in TRANSPORTS.get(service, ()) else DEFAULT_TRANSPORT[service]


def _state_doc() -> Dict[str, Any]:
    try:
        doc = json.loads((STATE_DIR / "state.json").read_text())
        return doc if isinstance(doc, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _vnc_status() -> Dict[str, Any]:
    version = _vnc_version()
    protocols = wayland_protocols()
    missing = [p for p in VNC_REQUIRED_PROTOCOLS if p not in set(protocols.get("protocols") or [])]
    active = _systemctl_active(VNC_SERVICE)
    listening = _listener(FIXED_PORTS["vnc"])
    clients = _vnc_clients() if listening else {"count": 0, "available": False}
    if not version:
        state = "UNSUPPORTED"
        reason = "wayvnc is not installed"
    elif missing:
        state = "UNSUPPORTED"
        reason = "Phoc does not advertise: " + ", ".join(missing)
    elif listening and not active:
        state = "ERROR"
        reason = ("A wayvnc listener is open but the managed unit is not active; "
                  "stop the unmanaged process and use the Bridge start action")
    elif clients.get("count", 0) > 0:
        state = "CONNECTED"
        reason = "An authenticated SSH-tunnel VNC client is connected"
    elif not active or not listening:
        state = "OFF"
        reason = "Service is stopped by default"
    else:
        state = "WAITING_FOR_CLIENT"
        reason = "wayvnc is ready and capturing the active Phoc output"
    st = _state_doc().get("vnc", {})
    return {
        "service": "vnc",
        "title": "VNC Screen Sharing",
        "state": state,
        "reason": reason,
        "session_mode": "current-wayland-session",
        "session_mode_label": "Mirrors the active Phoc/Wayland session",
        "preferred_transport": _preferred("vnc"),
        "active_transport": "wlan" if active else None,
        "interface": (network_state().get("interface") if active else None),
        "bind_address": LOOPBACK,
        "port": FIXED_PORTS["vnc"],
        "listener_verified": listening,
        "authenticated_clients": int(clients.get("count", 0)),
        "clients": clients.get("clients", []),
        "client_status_available": bool(clients.get("available")),
        "authentication": "SSH_TUNNEL",
        "encrypted": True,
        "encrypted_detail": "Loopback-only listener; access requires the owner's pinned-key SSH tunnel",
        "tls_fingerprint": None,
        "installed": bool(version),
        "version": version,
        "protocols": protocols,
        "missing_protocols": missing,
        "started_at": st.get("started_at"),
        "last_error": None if version and not missing else reason,
        "usb": usb_network_status(),
    }


def _xrdp_status() -> Dict[str, Any]:
    xrdp = _which("xrdp")
    xorg = _which("Xorg")
    active = _systemctl_active("xrdp.service") and _systemctl_active("xrdp-sesman.service")
    listening = _listener(FIXED_PORTS["xrdp"])
    sessions = _xrdp_sessions()
    fp = _xrdp_fingerprint()
    if not xrdp or not xorg:
        state = "UNSUPPORTED"
        reason = "xrdp or Xorg is not installed"
    elif not active or not listening:
        state = "OFF"
        reason = "Service is stopped by default"
    elif sessions.get("count", 0) > 0:
        state = "CONNECTED"
        reason = "An authenticated separate X11 session is active"
    else:
        state = "WAITING_FOR_CLIENT"
        reason = "xrdp is listening for the owner's RDP client"
    st = _state_doc().get("xrdp", {})
    return {
        "service": "xrdp",
        "title": "XRDP Remote Desktop",
        "state": state,
        "reason": reason,
        "session_mode": "separate-x11-session",
        "session_mode_label": "Separate remote X11 session (does not mirror the physical Phoc display)",
        "preferred_transport": _preferred("xrdp"),
        "active_transport": "wlan" if active else None,
        "interface": (network_state().get("interface") if active else None),
        "bind_address": LOOPBACK,
        "port": FIXED_PORTS["xrdp"],
        "listener_verified": listening,
        "authenticated_clients": int(sessions.get("count", 0)),
        "active_users": sessions.get("users", []),
        "authentication": "PAM_TLS",
        "encrypted": True,
        "encrypted_detail": "TLS 1.2/1.3; listener is loopback-only and reached through the SSH tunnel",
        "tls_fingerprint": fp,
        "installed": bool(xrdp and xorg),
        "version": "xrdp 0.10.6.1 / xorgxrdp 0.10.5" if xrdp else None,
        "started_at": st.get("started_at"),
        "last_error": _xrdp_last_error() if not active else None,
        "usb": usb_network_status(),
    }


def _adb_targets() -> Dict[str, Any]:
    adb = _which("adb")
    if not adb:
        return {"available": False, "targets": [], "error": "adb is not installed"}
    rc, out, err = _run([adb, "devices", "-l"], timeout=6)
    if rc != 0:
        return {"available": False, "targets": [], "error": (err or out).strip()[:300]}
    targets: List[Dict[str, Any]] = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        meta: Dict[str, str] = {}
        for token in parts[2:]:
            if ":" in token:
                k, v = token.split(":", 1)
                meta[k] = v
        targets.append({"serial": serial, "state": state,
                        "model": meta.get("model", ""),
                        "device": meta.get("device", ""),
                        "transport": "usb" if ":" not in serial else "tcpip"})
    return {"available": True, "targets": targets, "adb_version": _adb_version()}


def _adb_version() -> Optional[str]:
    adb = _which("adb")
    if not adb:
        return None
    rc, out, err = _run([adb, "version"], timeout=3)
    return (out or err).splitlines()[0].strip() if (out or err) else None


def _scrcpy_version() -> Optional[str]:
    exe = _which("scrcpy")
    if not exe:
        return None
    rc, out, err = _run([exe, "--version"], timeout=3)
    return (out or err).splitlines()[0].strip() if (out or err) else "installed"


def _scrcpy_status() -> Dict[str, Any]:
    adb = _adb_targets()
    scrcpy = _scrcpy_version()
    targets = adb.get("targets", [])
    native_nuxel = os.path.isdir("/usr/lib/nuxel") and not os.path.exists("/system/build.prop")
    if not adb.get("available"):
        state, reason = "UNSUPPORTED", "adb is not installed"
    elif not targets and native_nuxel:
        state = "NOT_APPLICABLE_NATIVE_NUXEL"
        reason = ("scrcpy supports Android ADB targets. This handset runs native "
                  "Nuxel Linux, not Android; use VNC Screen Sharing for native Nuxel.")
    elif not targets:
        state, reason = "NO_ANDROID_TARGET", "No Android ADB target is attached"
    elif not scrcpy:
        state = "UNSUPPORTED_NO_SCRCPY_BINARY"
        reason = ("Fedora 43 aarch64 does not ship an official scrcpy package; "
                  "the target is present but no official scrcpy client is installed.")
    else:
        state, reason = "READY", "Android target(s) detected"
    return {
        "service": "scrcpy",
        "title": "scrcpy (Android)",
        "state": state,
        "reason": reason,
        "session_mode": "android-adb-target",
        "session_mode_label": "Android ADB screen mirroring only; never native Nuxel",
        "preferred_transport": _preferred("scrcpy"),
        "active_transport": targets[0]["transport"] if targets else None,
        "interface": None,
        "bind_address": None,
        "port": None,
        "listener_verified": False,
        "authenticated_clients": 0,
        "authentication": "ADB_AUTHORIZATION",
        "encrypted": False,
        "encrypted_detail": "ADB USB/TCP-IP authorization; no VNC/RDP encryption involved",
        "targets": targets,
        "target_count": len(targets),
        "adb_available": bool(adb.get("available")),
        "adb_version": adb.get("adb_version"),
        "scrcpy_available": bool(scrcpy),
        "scrcpy_version": scrcpy,
        "native_nuxel": native_nuxel,
        "native_nuxel_note": ("scrcpy is not a native Nuxel screen-sharing protocol. "
                              "Use VNC Screen Sharing to mirror the Phoc session."),
        "usb": usb_network_status(),
    }


def get_status(service: Optional[str] = None) -> Dict[str, Any]:
    services = {"vnc": _vnc_status, "xrdp": _xrdp_status, "scrcpy": _scrcpy_status}
    if service is not None and service not in services:
        return {"success": False, "error": "unknown service", "error_code": "INVALID_SERVICE"}
    selected = {service: services[service]()} if service else {k: fn() for k, fn in services.items()}
    net = network_state()
    active = any(s.get("listener_verified") for s in selected.values()) or any(
        s.get("authenticated_clients", 0) > 0 for s in selected.values())
    return {
        "success": True,
        "schema": SCHEMA,
        "version": VERSION,
        "services": selected,
        "service": service,
        "network": net,
        "privacy": {
            "active": active,
            "indicator": "REMOTE DESKTOP ACTIVE" if active else "off",
            "kill_switch_available": True,
        },
        "defaults": dict(DEFAULT_TRANSPORT),
        "policy": {
            "off_by_default": True,
            "lan_scoped": True,
            "loopback_listener": True,
            "requires_ssh_tunnel": True,
            "usb_status": usb_network_status().get("status"),
        },
        "timestamp": time.time(),
    }


def privacy_summary() -> Dict[str, Any]:
    doc = get_status()
    return {"active": bool(doc.get("privacy", {}).get("active")),
            "services": {k: {"state": v.get("state"),
                             "active": bool(v.get("listener_verified")),
                             "clients": v.get("authenticated_clients", 0)}
                         for k, v in doc.get("services", {}).items()},
            "indicator": doc.get("privacy", {}).get("indicator", "off")}


def _helper(action: str, service: Optional[str] = None) -> Dict[str, Any]:
    args = [HELPER, action]
    if service:
        args.append(service)
    rc, out, err = _run(args, timeout=25)
    try:
        doc = json.loads(out) if out.strip().startswith("{") else None
    except json.JSONDecodeError:
        doc = None
    if doc is None:
        doc = {"success": rc == 0, "output": out.strip()[-1000:], "error": err.strip()[-1000:]}
    doc["helper_rc"] = rc
    return doc


def _write_preferences(service: str, transport: str) -> None:
    prefs = _preferences()
    prefs[service] = transport
    PREF_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = PREF_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(prefs, sort_keys=True) + "\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, PREF_FILE)


def connection_info(service: str) -> Dict[str, Any]:
    if service not in SERVICES:
        return {"success": False, "error": "unknown service", "error_code": "INVALID_SERVICE"}
    net = network_state()
    host = net.get("address")
    port = FIXED_PORTS.get(service)
    fp = _xrdp_fingerprint() if service == "xrdp" else None
    if service == "scrcpy":
        return {"success": True, "service": "scrcpy",
                "detail": "scrcpy targets Android ADB devices only; native Nuxel is not an Android target.",
                "targets": _scrcpy_status().get("targets", [])}
    ssh_cmd = None
    jump_url = None
    # Jump Desktop profiles nux-vnc / nux-rdp point at these local ports.
    local_port = 13389 if service == "xrdp" else 15900
    if host:
        ssh_cmd = (f"ssh -i ~/.ssh/wicked_wqn_id_rsa -N "
                   f"-o StrictHostKeyChecking=yes "
                   f"-o UserKnownHostsFile=configs/nuxel/security/ssh/known_hosts "
                   f"-L {local_port}:127.0.0.1:{port} nuxel@{host}")
        jump_url = f"{'rdp' if service == 'xrdp' else 'vnc'}://127.0.0.1:{local_port}"
    return {
        "success": True,
        "service": service,
        "transport": "wlan",
        "host": host,
        "interface": net.get("interface"),
        "trusted_lan": net.get("trusted_lan"),
        "port": port,
        "bind_address": LOOPBACK,
        "ssh_tunnel_command": ssh_cmd,
        "jump_url": jump_url,
        "username": "nuxel-remote" if service == "xrdp" else None,
        "password_included": False,
        "tls_fingerprint": fp,
        "note": ("Listener is loopback-only. Use the pinned-key SSH tunnel; do not expose "
                 "3389/5900 directly to the LAN or Internet."),
    }


def handle(action: str, params: Optional[Dict[str, Any]] = None,
           app_id: Optional[str] = None) -> Dict[str, Any]:
    params = params or {}
    service = params.get("service")
    transport = params.get("transport")
    if service is not None and service not in SERVICES:
        return {"success": False, "error": "unknown service", "error_code": "INVALID_SERVICE"}
    if action == "status":
        return get_status(service)
    if action == "diagnose":
        return {"success": True, "service": service,
                "diagnostic": get_status(service),
                "bounded": True, "mutated": False}
    if action == "connection-info":
        if not service:
            return {"success": False, "error": "service is required", "error_code": "INVALID_SERVICE"}
        return connection_info(service)
    if action == "scrcpy-targets":
        return {"success": True, "targets": _scrcpy_status().get("targets", []),
                "state": _scrcpy_status().get("state")}
    if action == "set-transport":
        if not service or not transport:
            return {"success": False, "error": "service and transport are required",
                    "error_code": "INVALID_TRANSPORT"}
        if transport not in TRANSPORTS.get(service, ()):
            return {"success": False, "error": "transport not allowed for this service",
                    "error_code": "INVALID_TRANSPORT"}
        if transport == "usb":
            return {"success": False, "error": "USB network is blocked on this kernel",
                    "error_code": "BLOCKED_KERNEL_PANIC",
                    "usb": usb_network_status()}
        _write_preferences(service, transport)
        return {"success": True, "service": service, "preferred_transport": transport}
    if action in ("start", "stop"):
        if not service:
            return {"success": False, "error": "service is required", "error_code": "INVALID_SERVICE"}
        if service == "scrcpy":
            st = _scrcpy_status()
            return {"success": False, "error": st.get("reason"),
                    "error_code": st.get("state"), "status": st}
        if action == "start":
            if transport and transport not in TRANSPORTS.get(service, ()):
                return {"success": False, "error": "transport not allowed for this service",
                        "error_code": "INVALID_TRANSPORT"}
            if transport == "usb":
                return {"success": False, "error": "USB network is blocked on this kernel",
                        "error_code": "BLOCKED_KERNEL_PANIC", "usb": usb_network_status()}
        result = _helper(action, service)
        result.setdefault("success", False)
        result["status"] = get_status(service).get("services", {}).get(service)
        return result
    if action in ("stop-all", "kill-switch"):
        result = _helper("stop-all")
        result.setdefault("success", False)
        result["status"] = get_status()
        return result
    return {"success": False, "error": "unknown action", "error_code": "INVALID_ACTION"}


if __name__ == "__main__":  # pragma: no cover - operator smoke helper
    import sys
    print(json.dumps(get_status(sys.argv[1] if len(sys.argv) > 1 else None),
                     indent=2, sort_keys=True))
