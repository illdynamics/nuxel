#!/usr/bin/env python3
"""Nuxel Tri-Link status for the three Applications-window consoles.

This module is READ-ONLY.  It never enables a gadget, starts/stops sshd, opens
the serial port, changes a route or reads a private key.  It exists so the
Serial / USB SSH / Wi-Fi SSH app surfaces can report real state instead of
pretending a transport works.

The actual host-side transports live in tools/beta/live/nuxel_tri_link.py and
nuxel-live-ssh.py.  This module describes the *phone* side they connect to:

  serial  USB CDC-ACM gadget + the single-owner console lock
  wifi    a non-loopback IPv4 interface + an sshd listener + key-only policy
  usb     kernel/configfs USB-network capability (blocked on 4.14.253 by the
          measured NCM teardown panic; the report and pstore evidence are
          retained in the repository)

Every root and command runner is injectable for the offline tests.  A missing
fact is returned as unavailable/unknown; it is never guessed into "connected".
"""

from __future__ import annotations

import base64
import fcntl
import gzip
import hashlib
import os
import re
import socket
import struct
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

VERSION = "28000"

#: NUXEL-26000 physical evidence: the live Samsung-derived 4.14.253 kernel
#: panicked in ncm_free_inst when the experimental NCM configfs function was
#: torn down.  This is a hard blocker and must never be presented as "ready".
KNOWN_BAD_USB_KERNELS = {"4.14.253"}
USB_PANIC_EVIDENCE = "docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/"

DEFAULT_USER = "nuxel"
SSH_PORT = 22


def _env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


def _read(path: Path | str) -> Optional[str]:
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return None


def _read_bytes(path: Path | str) -> Optional[bytes]:
    try:
        return Path(path).read_bytes()
    except OSError:
        return None


def _dirs(path: Path | str) -> List[str]:
    try:
        return sorted(p.name for p in Path(path).iterdir() if p.is_dir())
    except OSError:
        return []


def kernel_release(proc_root: Path | str = "/proc") -> str:
    return _read(Path(proc_root) / "sys/kernel/osrelease") or ""


def kernel_config_text(release: str, proc_root: Path | str = "/proc",
                       boot_root: Path | str = "/boot") -> str:
    gz = Path(proc_root) / "config.gz"
    try:
        with gzip.open(gz, "rt", errors="replace") as fh:
            return fh.read()
    except OSError:
        pass
    text = _read(Path(boot_root) / ("config-%s" % release))
    return text or ""


def parse_kernel_config(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# ") and line.endswith(" is not set"):
            out[line[2:-len(" is not set")].strip()] = "n"
        elif "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip().strip('"')
    return out


def _run_ip(runner: Callable[..., subprocess.CompletedProcess]) -> Dict[str, Any]:
    """Read IPv4 addresses/default route using a fixed, read-only command."""
    try:
        addr = runner(["ip", "-4", "-o", "addr", "show"],
                      capture_output=True, text=True, timeout=3,
                      stdin=subprocess.DEVNULL)
        route = runner(["ip", "-4", "route", "show", "default"],
                       capture_output=True, text=True, timeout=3,
                       stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": str(exc), "interfaces": [], "default_interface": None}
    interfaces: List[Dict[str, str]] = []
    for line in (addr.stdout or "").splitlines():
        m = re.match(r"^\d+:\s+([^:\s]+)\s+inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", line)
        if m:
            interfaces.append({"name": m.group(1), "address": m.group(2),
                               "prefix": m.group(3)})
    default_iface = None
    m = re.search(r"\bdev\s+(\S+)", route.stdout or "")
    if m:
        default_iface = m.group(1)
    return {"error": None, "interfaces": interfaces,
            "default_interface": default_iface}


def _ip_state_native(proc_root: Path | str = "/proc",
                    net_root: Path | str = "/sys/class/net") -> Dict[str, Any]:
    """Read IPv4 addresses and the default interface without shelling out.

    The HTTP bridge is root, but the S10+ 4.14 kernel denies AF_INET socket
    creation to unprivileged UIDs.  An ioctl on an AF_INET datagram socket is
    still available to this root service.  Interface *names* come from sysfs,
    not socket.if_nameindex(): the unit's RestrictAddressFamilies deliberately
    excludes AF_NETLINK, which glibc's if_nameindex() uses.
    """
    interfaces: List[Dict[str, str]] = []
    errors: List[str] = []
    names = _dirs(net_root)
    try:
        import fcntl as _fcntl
    except ImportError:  # pragma: no cover - linux phone always has fcntl
        _fcntl = None
    if _fcntl is not None:
        for name in names:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    packed = struct.pack("256s", name.encode("utf-8")[:15])
                    addr = socket.inet_ntoa(_fcntl.ioctl(sock.fileno(), 0x8915, packed)[20:24])  # SIOCGIFADDR
                    try:
                        mask = socket.inet_ntoa(_fcntl.ioctl(sock.fileno(), 0x891B, packed)[20:24])  # SIOCGIFNETMASK
                        prefix = str(sum(bin(int(part)).count("1") for part in mask.split(".")))
                    except OSError:
                        prefix = ""
                finally:
                    sock.close()
                interfaces.append({"name": name, "address": addr, "prefix": prefix})
            except OSError as exc:
                errors.append("%s:%s" % (name, exc))
    default_iface = None
    text = _read(Path(proc_root) / "net" / "route") or ""
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[1] == "00000000":
            default_iface = fields[0]
            break
    return {"error": None, "interfaces": interfaces, "default_interface": default_iface,
            "interface_errors": errors}


def _pick_wifi_interface(ip_state: Dict[str, Any]) -> Optional[Dict[str, str]]:
    candidates = [i for i in ip_state.get("interfaces") or []
                  if i["name"] != "lo" and not i["name"].startswith(("usb", "ncm", "rndis"))]
    if not candidates:
        return None
    default = ip_state.get("default_interface")
    for iface in candidates:
        if iface["name"] == default:
            return iface
    for iface in candidates:
        if iface["name"].startswith(("wlan", "wlp", "wifi")):
            return iface
    return candidates[0]


def _listening_sockets(proc_root: Path | str = "/proc") -> List[Dict[str, Any]]:
    """Return TCP LISTEN sockets (state 0A) from /proc/net/tcp{,6}."""
    out: List[Dict[str, Any]] = []
    for name in ("tcp", "tcp6"):
        text = _read(Path(proc_root) / "net" / name)
        if not text:
            continue
        for line in text.splitlines():
            if "local_address" in line:
                continue
            fields = line.split()
            if len(fields) < 4 or fields[3].upper() != "0A":
                continue
            host_hex, _, port_hex = fields[1].partition(":")
            try:
                port = int(port_hex, 16)
            except ValueError:
                continue
            out.append({"proto": name, "local_hex": host_hex, "port": port})
    return out


def _port_listening(port: int, proc_root: Path | str = "/proc") -> bool:
    return any(s["port"] == int(port) for s in _listening_sockets(proc_root))


def _parse_sshd_config(root: Path | str = "/etc/ssh") -> Dict[str, Any]:
    """Merge the main config and lexical drop-ins; later entries win.

    Only the policy facts shown in the UI are extracted.  No key material and
    no user credentials are returned.
    """
    base = Path(root)
    files: List[Path] = []
    main = base / "sshd_config"
    if main.is_file():
        files.append(main)
    drop = base / "sshd_config.d"
    try:
        files.extend(sorted(p for p in drop.iterdir() if p.is_file() and p.suffix == ".conf"))
    except OSError:
        pass
    facts: Dict[str, Any] = {"files": [str(p) for p in files],
                             "password_authentication": None,
                             "kbd_interactive_authentication": None,
                             "permit_root_login": None,
                             "allow_users": []}
    for path in files:
        text = _read(path) or ""
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^(PasswordAuthentication|KbdInteractiveAuthentication|"
                         r"PermitRootLogin|AllowUsers)\s+(.+)$", line, re.I)
            if not m:
                continue
            key, value = m.group(1).lower(), m.group(2).strip()
            if key == "allowusers":
                # Match OpenSSH's accumulate semantics across drop-ins.
                facts["allow_users"].extend(value.split())
            elif key == "passwordauthentication":
                facts["password_authentication"] = value.lower()
            elif key == "kbdinteractiveauthentication":
                facts["kbd_interactive_authentication"] = value.lower()
            else:
                facts["permit_root_login"] = value.lower()
    facts["key_only"] = (facts["password_authentication"] == "no" and
                         facts["kbd_interactive_authentication"] == "no")
    return facts


def _authorized_key_count(ssh_dir: Path | str = "/home/nuxel/.ssh") -> Optional[int]:
    """Count authorization entries, or None when the sandbox cannot see them.

    nuxel-http-bridge runs with ProtectHome=yes, so /home/nuxel is deliberately
    hidden from the status service.  That must read as UNKNOWN, never as "no
    keys" (which would falsely mark a working SSH endpoint unavailable).
    """
    path = Path(ssh_dir) / "authorized_keys"
    try:
        text = path.read_text(errors="replace")
    except FileNotFoundError:
        # Distinguish a readable empty/missing file from an unreadable home.
        return 0 if Path(ssh_dir).is_dir() else None
    except OSError:
        return None
    return sum(1 for line in text.splitlines()
               if line.strip() and not line.lstrip().startswith("#"))


def _host_key_fingerprint(ssh_dir: Path | str = "/etc/ssh") -> Dict[str, str]:
    """Compute the Ed25519 host-key fingerprint; never read a private key."""
    for name in ("ssh_host_ed25519_key.pub", "ssh_host_ecdsa_key.pub",
                 "ssh_host_rsa_key.pub"):
        text = _read(Path(ssh_dir) / name)
        if not text:
            continue
        fields = text.split()
        if len(fields) < 2:
            continue
        try:
            blob = base64.b64decode(fields[1], validate=True)
        except Exception:  # noqa: BLE001 - malformed key is simply unknown
            continue
        digest = base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
        return {"status": "present", "type": fields[0], "fingerprint": "SHA256:" + digest,
                "source": name}
    return {"status": "missing", "type": None, "fingerprint": None, "source": None}


def _flock_state(path: Path | str) -> str:
    p = Path(path)
    try:
        fd = os.open(p, os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
    except FileNotFoundError:
        return "absent"
    except PermissionError:
        try:
            fd = os.open(p, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
        except OSError:
            return "unknown"
    except OSError:
        return "unknown"
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            return "free"
        except BlockingIOError:
            return "held"
    finally:
        os.close(fd)


def _usb_function_names(gadget_root: Path | str = "/sys/kernel/config/usb_gadget") -> List[str]:
    names: List[str] = []
    for gadget in _dirs(gadget_root):
        names.extend(_dirs(Path(gadget_root) / gadget / "functions"))
    return sorted(set(names))


def _udc_state(udc_root: Path | str = "/sys/class/udc") -> Dict[str, Optional[str]]:
    return {name: _read(Path(udc_root) / name / "state") for name in _dirs(udc_root)}


def _net_interfaces(net_root: Path | str = "/sys/class/net") -> List[str]:
    return _dirs(net_root)


def _transport(status: str, *, target: str = "", detail: str = "",
               checks: Optional[List[Dict[str, str]]] = None,
               command: str = "", auth: str = "") -> Dict[str, Any]:
    return {"status": status, "target": target, "detail": detail,
            "auth": auth, "host_command": command, "checks": checks or []}


def serial_status(*, gadget_root: Path | str = "/sys/kernel/config/usb_gadget",
                  tty_root: Path | str = "/sys/class/tty",
                  udc_root: Path | str = "/sys/class/udc",
                  lock_path: Path | str = "/run/nuxel-console.lock") -> Dict[str, Any]:
    functions = _usb_function_names(gadget_root)
    udcs = _udc_state(udc_root)
    tty_present = (Path(tty_root) / "ttyGS0").exists()
    lock = _flock_state(lock_path)
    checks = [
        {"name": "acm-gadget", "status": "OK" if "acm.usb0" in functions else "MISSING",
         "detail": ", ".join(functions) or "no gadget functions"},
        {"name": "ttyGS0", "status": "OK" if tty_present else "MISSING"},
        {"name": "udc", "status": "OK" if any(udcs.values()) else "MISSING",
         "detail": ", ".join("%s=%s" % (k, v or "?") for k, v in udcs.items())},
        {"name": "console-lock", "status": lock.upper(), "detail": str(lock_path)},
    ]
    if "acm.usb0" not in functions or not tty_present:
        return _transport("UNAVAILABLE", target="USB CDC-ACM", checks=checks,
                          detail="serial gadget is not present on this boot; recovery is not reachable")
    detail = "USB serial recovery path is present"
    if lock == "held":
        detail += "; a console owner currently holds the single-owner lock"
    return _transport("AVAILABLE", target="USB CDC-ACM (/dev/ttyACM* on host)",
                      detail=detail, checks=checks, auth="none (exclusive host console)",
                      command="./scripts/s10plus-debug-pack/nuxel-live.sh --run 'uname -a'")


def wifi_status(*, runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
                proc_root: Path | str = "/proc", ssh_dir: Path | str = "/etc/ssh",
                authorized_keys_dir: Path | str = "/home/nuxel/.ssh") -> Dict[str, Any]:
    ip_state = _run_ip(runner) if runner is not None else _ip_state_native(proc_root)
    iface = _pick_wifi_interface(ip_state)
    listening = _port_listening(SSH_PORT, proc_root)
    policy = _parse_sshd_config(ssh_dir)
    host_key = _host_key_fingerprint(ssh_dir)
    key_count = _authorized_key_count(authorized_keys_dir)
    checks = [
        {"name": "interface", "status": "OK" if iface else "MISSING",
         "detail": "%s %s" % (iface["name"], iface["address"]) if iface else "no non-loopback IPv4"},
        {"name": "sshd-listen", "status": "OK" if listening else "MISSING",
         "detail": "tcp/22" if listening else "no TCP listener on port 22"},
        {"name": "authentication", "status": "OK" if policy["key_only"] else "FAIL",
         "detail": "publickey only" if policy["key_only"] else
                   "PasswordAuthentication/KbdInteractiveAuthentication are not both disabled"},
        {"name": "host-key", "status": "OK" if host_key["status"] == "present" else "MISSING",
         "detail": host_key.get("fingerprint") or "no public host key"},
        {"name": "authorized-keys",
         "status": "OK" if (key_count or 0) > 0 else ("UNKNOWN" if key_count is None else "MISSING"),
         "detail": ("unreadable to the status service (ProtectHome); host auth is authoritative"
                    if key_count is None else "%d key(s)" % key_count)},
    ]
    if not iface:
        return _transport("UNAVAILABLE", target="Wi-Fi", checks=checks,
                          detail="no Wi-Fi IPv4 address; the target is never guessed")
    target = "%s@%s:%d" % (DEFAULT_USER, iface["address"], SSH_PORT)
    command = ("./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport wlan "
               "--host %s --status" % iface["address"])
    if not listening:
        return _transport("UNAVAILABLE", target=target, checks=checks, command=command,
                          detail="sshd is not listening on TCP/22")
    if not policy["key_only"]:
        return _transport("UNAVAILABLE", target=target, checks=checks, command=command,
                          detail="ssh policy is not key-only; refusing to call this secure")
    if key_count == 0:
        return _transport("UNAVAILABLE", target=target, checks=checks, command=command,
                          detail="no authorized public key for the nuxel account")
    detail = "sshd is listening; %s is verified on the host" % host_key.get("fingerprint")
    if key_count is None:
        detail += "; authorized_keys is not visible to this sandboxed status service"
    return _transport("AVAILABLE", target=target, checks=checks, auth="publickey only",
                      detail=detail, command=command)


def usb_status(*, release: str = "",
               gadget_root: Path | str = "/sys/kernel/config/usb_gadget",
               net_root: Path | str = "/sys/class/net",
               proc_root: Path | str = "/proc",
               kernel_config: Optional[str] = None) -> Dict[str, Any]:
    release = release or kernel_release(proc_root)
    cfg = parse_kernel_config(kernel_config if kernel_config is not None
                              else kernel_config_text(release, proc_root))
    functions = _usb_function_names(gadget_root)
    interfaces = _net_interfaces(net_root)
    net_ifaces = [i for i in interfaces if i.startswith(("usb", "ncm", "rndis"))]
    compiled = {
        "ncm": cfg.get("CONFIG_USB_CONFIGFS_NCM") == "y" and cfg.get("CONFIG_USB_F_NCM") == "y",
        "rndis": cfg.get("CONFIG_USB_CONFIGFS_RNDIS") == "y" and cfg.get("CONFIG_USB_F_RNDIS") == "y",
        "ecm": cfg.get("CONFIG_USB_CONFIGFS_ECM") == "y",
        "configfs": cfg.get("CONFIG_USB_CONFIGFS") == "y",
    }
    checks = [
        {"name": "kernel", "status": "BLOCKED" if release in KNOWN_BAD_USB_KERNELS else "OK",
         "detail": release or "unknown"},
        {"name": "configfs", "status": "OK" if compiled["configfs"] else "MISSING"},
        {"name": "net-function", "status": "OK" if any(compiled[k] for k in ("ncm", "rndis", "ecm")) else "MISSING",
         "detail": ", ".join(k for k in ("ncm", "rndis", "ecm") if compiled[k]) or "none compiled"},
        {"name": "gadget-functions", "status": "OK" if any(f.startswith(("ncm.", "rndis.", "ecm.")) for f in functions) else "MISSING",
         "detail": ", ".join(functions) or "none"},
        {"name": "usb-network", "status": "OK" if net_ifaces else "MISSING",
         "detail": ", ".join(net_ifaces) or "usb0/ncm0/rndis0 absent"},
    ]
    if release in KNOWN_BAD_USB_KERNELS:
        return _transport(
            "BLOCKED_KERNEL_PANIC", target="USB network", checks=checks,
            detail=("unsupported on kernel %s: NCM configfs teardown panicked this build "
                    "(ncm_free_inst); evidence: %s" % (release, USB_PANIC_EVIDENCE)))
    if not compiled["configfs"] or not any(compiled[k] for k in ("ncm", "rndis", "ecm")):
        return _transport("BLOCKED_KERNEL", target="USB network", checks=checks,
                          detail="the kernel does not provide a usable USB network gadget")
    if not net_ifaces:
        return _transport("SUPPORTED_NOT_ENABLED", target="USB network", checks=checks,
                          detail="kernel support exists, but no usb0/ncm0/rndis0 interface is present")
    if not _port_listening(SSH_PORT, proc_root):
        return _transport("UNAVAILABLE", target="USB network", checks=checks,
                          detail="USB network interface exists, but sshd is not listening")
    return _transport("AVAILABLE", target="%s@usb-network:%d" % (DEFAULT_USER, SSH_PORT),
                      checks=checks, auth="publickey only",
                      detail="USB network interface present; SSH endpoint is listening",
                      command="./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport usb --status")


def get_status(*, release: str = "",
               runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
               proc_root: Path | str = "/proc",
               gadget_root: Path | str = "/sys/kernel/config/usb_gadget",
               tty_root: Path | str = "/sys/class/tty",
               udc_root: Path | str = "/sys/class/udc",
               net_root: Path | str = "/sys/class/net",
               ssh_dir: Path | str = "/etc/ssh",
               authorized_keys_dir: Path | str = "/home/nuxel/.ssh",
               lock_path: Path | str = "/run/nuxel-console.lock",
               kernel_config: Optional[str] = None) -> Dict[str, Any]:
    release = release or kernel_release(proc_root)
    return {
        "success": True,
        "schema": "nuxel.tri-link-status/1",
        "version": VERSION,
        "kernel_release": release,
        "transports": {
            "serial": serial_status(gadget_root=gadget_root, tty_root=tty_root,
                                    udc_root=udc_root, lock_path=lock_path),
            "wifi": wifi_status(runner=runner, proc_root=proc_root, ssh_dir=ssh_dir,
                                authorized_keys_dir=authorized_keys_dir),
            "usb": usb_status(release=release, gadget_root=gadget_root,
                              net_root=net_root, proc_root=proc_root,
                              kernel_config=kernel_config),
        },
    }
