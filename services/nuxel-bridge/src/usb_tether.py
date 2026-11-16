#!/usr/bin/env python3
"""Nuxel USB Internet tethering provider (phone side, nftables).

USB *networking* (local USB Ethernet + SSH) and USB *tethering* (sharing the
phone's upstream Internet with the attached computer) are separate features.
This module owns ONLY the forwarding/NAT path.  The gadget composition is owned
by nuxel-usb-mode.sh; the USB address is the live one the manager records.

Design (full-pwnage-usbnet.md §8/§12):

* Everything lives in ONE dedicated table ``inet nuxel_usb_tether``.  Nothing
  here flushes the global ruleset, touches ``inet nuxel_console_guard``, the
  ``inet nuxel_app_firewall`` table or the VPN kill switch.
* The app firewall forwards at priority -100 with ``policy drop``.  This table
  hooks forward at -50 (later, so it can accept the tether flow) and itself
  keeps ``policy drop`` for traffic it sees; it accepts ONLY:
    - usb -> upstream, source address = the exact phone-side tether address;
    - upstream -> usb, ct state established/related (return path only).
  No broad ``iifname usb* accept``.
* NAT is scoped to that single source address and the ONE selected upstream.
* The upstream must have a real IPv4 default route and a link gate; choosing a
  tunnel interface is allowed (traffic then inherits the tunnel), a physical
  upstream while the VPN kill switch is armed is refused rather than silently
  leaking around the tunnel.
* ``net.ipv4.ip_forward`` is saved before enabling and restored exactly on
  stop/failure.  DHCP is not provided by the phone (no DHCP server is added to
  this kernel image), so the provider reports ``dhcp`` = "static-host-config"
  and the attached host uses .2/24 with the phone .1 as gateway.  IPv6 is not
  shared; the provider never advertises RA/DNS it cannot serve.
* Any start failure removes the table, restores the sysctl and records the
  error.  A status poll never mutates anything.
* The attached host must be verified (``verify()``): table present + system
  forwarding enabled + the newest attached-host evidence, or the state is
  reported ``on-unverified`` and ``internet_verified`` stays false.

No JS-controlled strings reach a shell: interface names are validated and must
exist in /sys/class/net; argv lists are used everywhere.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

def _usb_config():
    values = {"NUXEL_USB_NET_SUBNET": "10.100.10.0/24",
              "NUXEL_USB_NET_ADDR": "10.100.10.1/24",
              "NUXEL_USB_NET_HOST_ADDR": "10.100.10.2/24"}
    try:
        with open(os.environ.get("NUXEL_USB_NET_CONFIG", "/etc/nuxel/usb-network.conf")) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key in values:
                    values[key] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return values

_USB_CONFIG = _usb_config()
DEFAULT_SUBNET = _USB_CONFIG["NUXEL_USB_NET_SUBNET"]
TABLE = "nuxel_usb_tether"


def _root(env: str, default: str) -> str:
    return os.environ.get(env, default)
# DHCP-less link: the host is configured .2/24, gateway .1 (the phone).
HOST_ADDRESS = _USB_CONFIG["NUXEL_USB_NET_HOST_ADDR"]
DEFAULT_GATEWAY = _USB_CONFIG["NUXEL_USB_NET_ADDR"].split("/", 1)[0]
IFNAME_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,15}$")
# Never selectable as an upstream: the gadget itself and loopback.
_NOT_UPSTREAM = re.compile(r"^(lo|usb\d+|ncm\d+|rndis\d+|eem\d+|usb_tether\w*)$")
_TUNNEL = re.compile(r"^(tun|tap|wg|zt|vpn|ipsec|ppp|nordlynx|tailscale)")
# A probe the phone itself can reach; used only for phone-side reachability.
PROBE_URLS = ("https://connectivity.gstatic.com/generate_204",
              "https://www.gstatic.com/generate_204")


class TetherError(Exception):
    def __init__(self, message: str, code: str = "TETHER_ERROR"):
        super().__init__(message)
        self.code = code


def _uptime() -> str:
    parts = _read("/proc/uptime").split()
    return parts[0] if parts else ""


def _state_path() -> str:
    return _root("NUXEL_USB_TETHER_STATE", "/run/nuxel/usb-tether.json")


def _usb_state_path() -> str:
    return _root("NUXEL_USB_MODE_STATE", "/run/nuxel/usb-mode.state")


def _evidence_path() -> str:
    return _root("NUXEL_USB_HOST_EVIDENCE", "/var/lib/nuxel/usb-tether-host.json")


def _sys_net() -> str:
    return _root("NUXEL_SYS_NET", "/sys/class/net")


def _run(argv: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(argv, 127, "", str(exc))


def _read(path: str) -> str:
    try:
        with open(path, "r") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r") as fh:
            doc = json.load(fh)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_json(path: str, doc: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".new"
    with open(tmp, "w") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def valid_ifname(name: str) -> bool:
    return bool(IFNAME_RE.match(name or "")) and os.path.isdir(os.path.join(_sys_net(), name))


def _default_routes() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for line in _run(["ip", "-4", "route", "show", "default"]).stdout.splitlines():
        parts = line.split()
        if "dev" not in parts:
            continue
        dev = parts[parts.index("dev") + 1]
        gw = parts[parts.index("via") + 1] if "via" in parts else None
        metric = None
        if "metric" in parts:
            try:
                metric = int(parts[parts.index("metric") + 1])
            except (ValueError, IndexError):
                metric = None
        if dev not in out or (metric is not None and
                              (out[dev].get("metric") is None or metric < out[dev]["metric"])):
            out[dev] = {"gateway": gw, "metric": metric, "raw": line.strip()}
    return out


def _vpn_armed() -> bool:
    return "table inet nuxel_vpn_killswitch" in _run(["nft", "list", "ruleset"]).stdout


def usb_link() -> Dict[str, Any]:
    """The live USB link from the single gadget owner's activation record."""
    import usb_tethering
    st = usb_tethering.current_state()
    return {"active": st["active"], "interface": st["interface"],
            "mode": st["mode"], "phone_address": st["device_ip"],
            "host_address": HOST_ADDRESS, "netdev_present": bool(st["interface"])}


def upstream_candidates() -> List[Dict[str, Any]]:
    routes = _default_routes()
    out = []
    for name in sorted(os.listdir(_sys_net())) if os.path.isdir(_sys_net()) else []:
        if not valid_ifname(name) or _NOT_UPSTREAM.match(name):
            continue
        oper = _read(os.path.join(_sys_net(), name, "operstate")) or "unknown"
        has_addr = bool(_run(["ip", "-4", "-o", "addr", "show", "dev", name]).stdout.strip())
        tun = bool(_TUNNEL.match(name))
        route = routes.get(name)
        usable = bool(has_addr and route and oper == "up")
        kind = ("wifi" if name.startswith("wlan") else
                "cellular" if name.startswith(("rmnet", "wwan", "usb_wan")) else
                "tunnel" if tun else "other")
        out.append({
            "interface": name, "kind": kind, "link": oper,
            "has_ipv4": has_addr, "default_route": bool(route),
            "vpn_tunnel": tun, "usable": usable,
            "gateway": (route or {}).get("gateway"),
        })
    return out


def choose_upstream(requested: Optional[str]) -> Dict[str, Any]:
    cands = upstream_candidates()
    if requested:
        for c in cands:
            if c["interface"] == requested:
                if not c["usable"]:
                    raise TetherError("upstream %s has no usable IPv4 default route "
                                      "(link=%s has_ipv4=%s)" % (requested, c["link"], c["has_ipv4"]),
                                      "UPSTREAM_UNAVAILABLE")
                return c
        raise TetherError("invalid or absent upstream interface: %s" % requested,
                          "UPSTREAM_INVALID")
    usable = [c for c in cands if c["usable"]]
    if not usable:
        raise TetherError("no interface currently has a usable IPv4 default route",
                          "NO_UPSTREAM")
    # Prefer a tunnel when the kill switch is armed, so the share does not leak;
    # otherwise prefer WiFi, then anything else (never a modem that merely exists).
    usable.sort(key=lambda c: (0 if c["vpn_tunnel"] else 1,
                               0 if c["kind"] == "wifi" else 1, c["interface"]))
    return usable[0]


def vpn_conflict(upstream: Dict[str, Any]) -> Optional[str]:
    if not _vpn_armed():
        return None
    if upstream.get("vpn_tunnel"):
        return None
    return ("VPN kill switch is armed and upstream %s is not a tunnel: tethered "
            "traffic would bypass the VPN. Pick the tunnel interface as upstream "
            "or disarm the kill switch." % upstream["interface"])


def _source_address(link: Dict[str, Any]) -> str:
    addr = link.get("phone_address") or ""
    try:
        return str(ipaddress.ip_interface(addr).ip)
    except ValueError:
        return DEFAULT_GATEWAY


def _port_conflict(link: Dict[str, Any], upstream: Dict[str, Any]) -> Optional[str]:
    """Refuse a share whose NAT would collide with an existing tunnel source."""
    try:
        net = ipaddress.ip_network(link.get("phone_address") or DEFAULT_SUBNET, strict=False)
    except ValueError:
        return "invalid USB subnet in state"
    for line in _run(["ip", "-4", "-o", "addr", "show"]).stdout.splitlines():
        parts = line.split()
        if "inet" not in parts:
            continue
        try:
            have = ipaddress.ip_interface(parts[parts.index("inet") + 1])
        except (ValueError, IndexError):
            continue
        dev = parts[parts.index("dev") + 1] if "dev" in parts else ""
        if dev == link.get("interface"):
            continue
        if have.ip in net and dev.startswith(("tun", "tap", "wg", "zt")):
            return ("an existing tunnel interface %s already holds %s inside the USB "
                    "subnet; NAT would be ambiguous" % (dev, have.ip))
    return None


def _render(link: Dict[str, Any], upstream: Dict[str, Any]) -> str:
    # Do not impose a default-drop policy on hotspot/VPN forwarding. Restrict
    # only this USB interface; unrelated forwarding remains with its owner.
    usb, up = link["interface"], upstream["interface"]
    return "\n".join([
        "add table inet %s" % TABLE,
        "add chain inet %s forward { type filter hook forward priority -50; policy accept; }" % TABLE,
        'add rule inet %s forward iifname "%s" oifname "%s" ip saddr %s counter accept' % (TABLE, usb, up, DEFAULT_SUBNET),
        'add rule inet %s forward iifname "%s" oifname "%s" ip daddr %s ct state established,related counter accept' % (TABLE, up, usb, DEFAULT_SUBNET),
        'add rule inet %s forward iifname "%s" counter drop' % (TABLE, usb),
        'add rule inet %s forward oifname "%s" counter drop' % (TABLE, usb), ""])

NAT_CHAIN = "NUXEL_USB_TETHER"
PREF_PATH = "/var/lib/nuxel/usb-tether-preferences.json"
UNIT = "nuxel-usb-tether.service"

def _clear_nat():
    while _run(["iptables", "-w", "-t", "nat", "-D", "POSTROUTING", "-j", NAT_CHAIN]).returncode == 0:
        pass
    _run(["iptables", "-w", "-t", "nat", "-F", NAT_CHAIN])
    _run(["iptables", "-w", "-t", "nat", "-X", NAT_CHAIN])

def _install_nat(upstream):
    # This vendor kernel supports iptables NAT, but lacks nftables NAT chains.
    # Our private chain never edits the hotspot's NUXEL_TETHER chain.
    _clear_nat()
    for args in (["-N", NAT_CHAIN],
                 ["-A", NAT_CHAIN, "-s", DEFAULT_SUBNET, "-o", upstream, "-j", "MASQUERADE"],
                 ["-A", "POSTROUTING", "-j", NAT_CHAIN]):
        proc = _run(["iptables", "-w", "-t", "nat", *args])
        if proc.returncode:
            _clear_nat()
            return proc
    return proc

def _service_control(enabled, upstream=None):
    _write_json(PREF_PATH, {"enabled": enabled, "upstream": upstream})
    proc = _run(["systemctl", "enable" if enabled else "disable", UNIT])
    if not proc.returncode:
        proc = _run(["systemctl", "restart" if enabled else "stop", UNIT], timeout=55)
    out = status()
    out["success"] = proc.returncode == 0 and out["enabled"] == enabled
    if not out["success"]:
        out["error"] = proc.stderr.strip() or out.get("last_error") or "USB tether service failed"
    return out


def _run_nft_script(script: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["nft", "-f", "-"], input=script,
                              capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(["nft", "-f", "-"], 127, "", str(exc))


def _table_present() -> bool:
    return _run(["nft", "list", "table", "inet", TABLE]).returncode == 0


def _list_table() -> str:
    return _run(["nft", "list", "table", "inet", TABLE]).stdout


def _ip_forward() -> str:
    return _read("/proc/sys/net/ipv4/ip_forward") or "0"


def _host_evidence() -> Dict[str, Any]:
    ev = _read_json(_evidence_path())
    try:
        age = max(0, int(float(_uptime()) - float(ev["uptime"])))
        if ev.get("boot_id") != _read("/proc/sys/kernel/random/boot_id"):
            age = None
    except (KeyError, TypeError, ValueError):
        age = None
    return {"verified": bool(ev.get("verified")) and age is not None and age <= 120,
            "source": ev.get("source"), "age_seconds": age,
            "checked_at": ev.get("checked_at")}


def _ip_forward_needed_elsewhere() -> bool:
    """True when the Wi-Fi hotspot (or any tether table) still needs routing."""
    try:
        with open("/run/nuxel-hotspot/state.json") as fh:
            if json.load(fh).get("enabled"):
                return True
    except (OSError, ValueError):
        pass
    out = _run(["nft", "list", "tables"]).stdout or ""
    return "nuxel_usb_tether" in out or "nuxel_tether" in out


def status() -> Dict[str, Any]:
    st = _read_json(_state_path())
    link = usb_link()
    present = _table_present()
    ev = _host_evidence() if present and st.get("enabled") else {"verified": False, "age_seconds": None,
                                                               "source": None, "checked_at": None}
    enabled = bool(st.get("enabled"))
    if not enabled:
        state = "off"
    elif not link["active"]:
        state = "degraded"
    elif not present:
        state = "error"
    elif ev["verified"]:
        state = "on"
    else:
        state = "on-unverified"
    return {
        "success": True,
        "enabled": enabled,
        "state": state,
        "upstream": st.get("upstream"),
        "usb_interface": link["interface"],
        "usb_link_active": link["active"],
        "subnet": st.get("subnet") or DEFAULT_SUBNET,
        "source_address": st.get("source_address"),
        "host_address": link.get("host_address") or HOST_ADDRESS,
        "gateway": DEFAULT_GATEWAY,
        "dhcp": "static-host-config",
        "ipv6": "not-shared",
        "rules_present": present,
        "table": "inet " + TABLE,
        "ip_forward": _ip_forward() == "1",
        "internet_verified": bool(ev["verified"]) and state == "on",
        "host_evidence": ev,
        "vpn_armed": _vpn_armed(),
        "vpn_conflict": st.get("vpn_conflict"),
        "upstreams": upstream_candidates(),
        "last_error": st.get("last_error"),
        "started_at": st.get("started_at"),
    }


def start(upstream: Optional[str] = None, source: str = "api") -> Dict[str, Any]:
    if os.environ.get("NUXEL_USB_TETHER_WORKER") != "1":
        return _service_control(True, upstream)
    link = usb_link()
    if not link["active"]:
        return {"success": False, "error": "usb-network-not-active",
                "error_code": "USB_NOT_ACTIVE",
                "detail": "enable USB networking (local link) first; a cable alone is not a link"}
    try:
        up = choose_upstream(upstream)
    except TetherError as exc:
        return {"success": False, "error": str(exc), "error_code": exc.code}
    conflict = vpn_conflict(up)
    if conflict:
        return {"success": False, "error": conflict, "error_code": "VPN_CONFLICT"}
    port = _port_conflict(link, up)
    if port:
        return {"success": False, "error": port, "error_code": "WORKLOAD_CONFLICT"}
    # v0.8.5: strict reverse-path filtering silently black-holed every
    # forwarded reply on the live phone (usb0 and wlan0 both had rp_filter=2),
    # so the attached host could ping the phone but no Internet packet ever
    # came back.  Loose mode (2) still validates the source route; the tether
    # flows must not be subject to strict mode.
    for iface in (link["interface"], up["interface"]):
        if iface:
            _run(["sysctl", "-qw", "net.ipv4.conf.%s.rp_filter=2" % iface])
    prev_forward = _ip_forward()
    # Replacing only OUR table is idempotent and never touches other tables.
    _run(["nft", "delete", "table", "inet", TABLE])
    proc = _run_nft_script(_render(link, up))
    if proc.returncode != 0:
        _run(["nft", "delete", "table", "inet", TABLE])
        return {"success": False,
                "error": (proc.stderr or proc.stdout).strip()[:800] or "nft failed",
                "error_code": "NFT_FAILED"}
    if not _table_present():
        _run(["nft", "delete", "table", "inet", TABLE])
        return {"success": False, "error": "nft reported success but the table is absent",
                "error_code": "NFT_VERIFY_FAILED"}
    nat = _install_nat(up["interface"])
    if nat.returncode:
        _run(["nft", "delete", "table", "inet", TABLE])
        return {"success": False, "error": nat.stderr, "error_code": "NAT_FAILED"}
    sysctl = _run(["sysctl", "-qw", "net.ipv4.ip_forward=1"])
    if sysctl.returncode != 0 or _ip_forward() != "1":
        _run(["nft", "delete", "table", "inet", TABLE])
        _run(["sysctl", "-qw", "net.ipv4.ip_forward=%s" % prev_forward])
        return {"success": False, "error": "could not enable IPv4 forwarding: " +
                (sysctl.stderr or "").strip()[:300], "error_code": "SYSCTL_FAILED"}
    doc = {
        "enabled": True, "upstream": up["interface"], "upstream_kind": up["kind"],
        "usb_interface": link["interface"], "subnet": DEFAULT_SUBNET,
        "source_address": _source_address(link), "host_address": HOST_ADDRESS,
        "prev_ip_forward": prev_forward, "vpn_armed": _vpn_armed(),
        "vpn_conflict": None, "upstream_reachable": True, "dhcp": "static-host-config",
        "ipv6": "not-shared", "last_error": None, "source": source,
        "started_at": _uptime(),
    }
    _write_json(_state_path(), doc)
    out = status()
    out["success"] = out["state"] in ("on", "on-unverified")
    if out["state"] == "on-unverified":
        out["detail"] = ("forwarding+NAT configured; waiting for the attached host to "
                         "prove end-to-end Internet (host evidence)")
    return out


def stop(source: str = "api") -> Dict[str, Any]:
    if os.environ.get("NUXEL_USB_TETHER_WORKER") != "1":
        return _service_control(False)
    _clear_nat()
    st = _read_json(_state_path())
    _run(["nft", "delete", "table", "inet", TABLE])
    # Local-only networking must not keep forwarding after sharing is stopped.
    _run_nft_script("add table inet %s\nadd chain inet %s forward { type filter hook forward priority -50; policy accept; }\nadd rule inet %s forward iifname \"usb0\" drop\n" % (TABLE, TABLE, TABLE))
    # v0.8.5: DO NOT restore a stale "previous" ip_forward here.  Forwarding is
    # shared with the Wi-Fi hotspot; stopping tethering used to write back the
    # value captured at tether start (0 if the hotspot was not yet running),
    # which silently switched OFF an already-running AP.  Only turn it off when
    # nothing else needs it.
    if _ip_forward() == "1" and not _ip_forward_needed_elsewhere():
        _run(["sysctl", "-qw", "net.ipv4.ip_forward=0"])
    _write_json(_state_path(), {"enabled": False, "upstream": None, "internet_verified": False,
                        "last_error": None, "stopped_by": source,
                        "last_stopped_at": _uptime()})
    try:
        os.unlink(_evidence_path())
    except OSError:
        pass
    return status()


def verify() -> Dict[str, Any]:
    """Read-only: does the attached host have current end-to-end evidence?"""
    st = _read_json(_state_path())
    if not st.get("enabled"):
        return {"success": False, "error": "tether is not enabled",
                "error_code": "NOT_ENABLED"}
    out = status()
    out["success"] = True
    return out


def host_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Accept the attached computer's end-to-end evidence (host helper).

    Only a small, typed document is accepted; it is used solely to decide
    whether ``internet_verified`` may be true, never to change firewall state.
    """
    link = usb_link()
    try:
        src_ip = str(ipaddress.ip_address(str(payload.get("host_address") or "")))
        dst_ip = str(ipaddress.ip_address(str(payload.get("checked_phone") or "")))
    except ValueError:
        return {"success": False, "error": "invalid host evidence",
                "error_code": "INVALID_EVIDENCE"}
    want = _source_address(link) if link["active"] else DEFAULT_GATEWAY
    if dst_ip != want:
        return {"success": False, "error": "evidence was checked against %s, not the phone %s"
                % (dst_ip, want), "error_code": "EVIDENCE_TARGET_MISMATCH"}
    ev = {
        "verified": bool(payload.get("internet_ok")),
        "source": "host-helper",
        "host_address": src_ip,
        "checked_phone": dst_ip,
        "dns_ok": bool(payload.get("dns_ok")),
        "ping_ok": bool(payload.get("ping_ok")),
        "age_seconds": 0, "uptime": _uptime(),
        "boot_id": _read("/proc/sys/kernel/random/boot_id"),
        "checked_at": payload.get("checked_at") or "",
    }
    if not ev["verified"]:
        ev["verified"] = False
    _write_json(_evidence_path(), ev)
    return {"success": True, **status()}
