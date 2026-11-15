#!/usr/bin/python3
"""Nuxel Wi-Fi hotspot (hostapd + dnsmasq + scoped nftables NAT).

Why this exists
---------------
The NetworkManager/nmcli hotpot path cannot work on this image: there is no
udev daemon, so NetworkManager never enumerates the Broadcom phy as a managed
Wi-Fi device, and `nmcli device wifi hotspot` therefore always fails.  The
vendor driver *does* advertise AP mode (it permits up to two AP interfaces on
two channels), so the phone can host an AP directly.

Design
------
* A SECOND vif of the same phy (`wlan1`) is dedicated to the AP.  The uplink
  stays on `wlan0`, so the AP does not disturb the owner's Wi-Fi connection.
* hostapd owns the 802.11 side.  dnsmasq serves DHCP + DNS on the AP interface
  only (bind-interfaces, interface=<ap>).  Neither daemon is left running when
  the hotspot is off.
* NAT is a DEDICATED nftables table `inet nuxel_hotspot`, forward hook at
  priority -50 (after the app firewall's -100 drop), masquerade scoped to the
  AP subnet and the chosen uplink.  It never flushes the global ruleset and
  never touches `nuxel_app_firewall`, `nuxel_console_guard`, `nuxel_tether` or
  the VPN kill switch.
* Everything is idempotent; `stop` always removes hostapd, dnsmasq, the table
  and the AP address, even if a previous start was interrupted.
* IPv6 is not shared and no RA is advertised.

Control surface (root only):
    nuxel-hotspot start --ssid NAME --password PASS [--interface wlan1]
    nuxel-hotspot status
    nuxel-hotspot stop
The same logic is callable from the bridge through network_manager.hotspot_*.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

AP_SUBNET = "10.42.0.0/24"
AP_ADDRESS = "10.42.0.1"
AP_CIDR = AP_ADDRESS + "/24"
AP_CHANNEL = os.environ.get("NUXEL_HOTSPOT_CHANNEL", "6")
AP_COUNTRY = os.environ.get("NUXEL_HOTSPOT_COUNTRY", "NL")
TABLE = "nuxel_hotspot"
RUN = "/run/nuxel-hotspot"
CONF_DIR = "/etc/nuxel/hotspot"
STATE = RUN + "/state.json"
SSID_RE = re.compile(r"^[ -~]{1,32}$")
PSK_RE = re.compile(r"^[ -~]{8,63}$")
IFACE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,15}$")


def log(msg: str) -> None:
    print("nuxel-hotspot: %s" % msg, file=sys.stderr, flush=True)


def run(argv, timeout=25.0):
    try:
        return subprocess.run(list(argv), capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(list(argv), 127, "", str(exc))


def _default_uplink() -> str:
    """The interface carrying the real IPv4 default route.

    This must never be the AP vif (wlan1) nor a tether gadget: masquerading AP
    traffic onto the AP itself is a no-op loop.  A secondary Wi-Fi vif on the
    same phy has no default route, so the first non-gadget device wins.
    """
    out = run(["/usr/sbin/ip", "-4", "route", "show", "default"]).stdout
    for line in out.splitlines():
        parts = line.split()
        if "dev" not in parts:
            continue
        dev = parts[parts.index("dev") + 1]
        if dev in ("lo", "wlan1", "p2p0"):
            continue
        if dev.startswith(("usb", "ncm", "rndis")):
            continue
        if os.path.exists("/sys/class/net/" + dev):
            return dev
    # Fallback: the interface that has a real IPv4 address on the LAN and is
    # not a gadget or the AP vif (some boots show the default route with a
    # link-local-only device first).
    for name in sorted(os.listdir("/sys/class/net")):
        if name in ("lo", "wlan1", "p2p0") or name.startswith(("usb", "ncm", "rndis")):
            continue
        addr = run(["/usr/sbin/ip", "-4", "addr", "show", name]).stdout
        if re.search(r"inet (?!169\.254\.)\d+\.", addr):
            return name
    return ""


def _ap_capable_interface(requested: str | None) -> tuple[str, str]:
    """Return (interface, reason).  Never guesses: the vif must exist, or a
    second vif must be creatable from an existing station interface."""
    if requested:
        if not IFACE_RE.match(requested):
            return "", "invalid interface name"
        if not os.path.exists("/sys/class/net/" + requested):
            added = run(["/usr/sbin/iw", "dev", "wlan0", "interface", "add", requested,
                         "type", "__ap"]).returncode
            if added != 0:
                return "", "interface %s absent and could not be created" % requested
        return requested, ""
    iw = run(["/usr/sbin/iw", "dev"])
    if iw.returncode != 0:
        return "", "iw/nl80211 unavailable"
    ifaces = re.findall(r"^\s*Interface\s+(\S+)", iw.stdout, re.M)
    # Prefer an interface that is not the current uplink.
    uplink = _default_uplink()
    candidates = [i for i in ifaces if i != uplink]
    if not candidates:
        return "", "no secondary Wi-Fi interface for the AP"
    return candidates[0], ""


def _phy_supports_ap(iface: str) -> tuple[bool, str]:
    phy = os.path.realpath("/sys/class/net/%s/phy80211" % iface)
    try:
        out = run(["/usr/sbin/iw", "list"]).stdout
    except Exception:
        out = ""
    if not out:
        info = pathlib_read(phy + "/index")
        return False, "iw list unavailable (phy index %s)" % info
    if "* AP" in out and "valid interface combinations" in out:
        return True, ""
    return False, "nl80211 does not advertise AP mode"


def pathlib_read(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return "?"


def write_hostapd_conf(iface: str, ssid: str, password: str) -> str:
    os.makedirs(RUN, mode=0o755, exist_ok=True)
    conf = RUN + "/hostapd.conf"
    body = (
        "# Generated by nuxel-hotspot - do not edit.\n"
        "driver=nl80211\n"
        "interface=%s\n"
        "ctrl_interface=%s/ctrl\n"
        "ssid=%s\n"
        "hw_mode=g\n"
        "channel=%s\n"
        "country_code=%s\n"
        "ieee80211d=1\n"
        "wmm_enabled=1\n"
        "auth_algs=1\n"
        "wpa=2\n"
        "wpa_key_mgmt=WPA-PSK\n"
        "rsn_pairwise=CCMP\n"
        "wpa_passphrase=%s\n"
        "macaddr_acl=0\n"
        "ignore_broadcast_ssid=0\n"
    ) % (iface, RUN, ssid, AP_CHANNEL, AP_COUNTRY, password)
    with open(conf, "w") as f:
        f.write(body)
    os.chmod(conf, 0o600)
    return conf


def write_dnsmasq_conf(iface: str) -> str:
    conf = RUN + "/dnsmasq.conf"
    body = (
        "# Generated by nuxel-hotspot - do not edit.\n"
        "interface=%s\n"
        "bind-interfaces\n"
        "except-interface=lo\n"
        "listen-address=%s\n"
        "dhcp-range=%s.10,%s.200,255.255.255.0,12h\n"
        "dhcp-option=option:router,%s\n"
        "dhcp-option=option:dns-server,%s\n"
        "dhcp-leasefile=%s/leases\n"
        "pid-file=%s/dnsmasq.pid\n"
        "no-hosts\n"
        "log-facility=%s/dnsmasq.log\n"
    ) % (iface, AP_ADDRESS, AP_ADDRESS.rsplit(".", 1)[0], AP_ADDRESS.rsplit(".", 1)[0],
         AP_ADDRESS, AP_ADDRESS, RUN, RUN, RUN)
    with open(conf, "w") as f:
        f.write(body)
    return conf


NAT_RULES = """table inet {table} {{
    chain forward {{
        type filter hook forward priority -50; policy accept;
        iifname "{ap}" oifname "{up}" accept
        iifname "{up}" oifname "{ap}" ct state established,related accept
    }}
    chain postrouting {{
        type nat hook postrouting priority srcnat; policy accept;
        ip saddr {subnet} oifname "{up}" masquerade
    }}
}}
"""

# This kernel is built WITHOUT loadable modules (/lib/modules is absent) and
# only the legacy iptables NAT path is available: nftables' `masquerade`
# statement needs the nf_nat module to be resolvable at chain-create time and
# fails with ENOENT, while iptables-legacy reaches the built-in NAT directly.
# The hotspot therefore uses its own dedicated iptables chains - never the
# global-flush `iptables` sharing backend and never the tether chain - and
# falls back to them only when the nftables NAT hook cannot be created.
IPT_CHAIN_FWD = "NUXEL_HOTSPOT_FWD"
IPT_CHAIN_NAT = "NUXEL_HOTSPOT_NAT"


IPTABLES = shutil.which("iptables") or "/usr/sbin/iptables"


def _ipt(*args):
    return run([IPTABLES] + list(args))


def _apply_nat_nft(ap: str, uplink: str) -> tuple[bool, str]:
    run(["/usr/sbin/nft", "delete", "table", "inet", TABLE])
    rules = NAT_RULES.format(table=TABLE, ap=ap, up=uplink, subnet=AP_SUBNET)
    proc = subprocess.run(["/usr/sbin/nft", "-f", "-"], input=rules, text=True,
                          capture_output=True)
    if proc.returncode != 0:
        return False, (proc.stderr or "").strip()[:300]
    return True, ""


def _apply_nat_ipt(ap: str, uplink: str) -> tuple[bool, str]:
    errs = []
    _ipt("-t", "nat", "-N", IPT_CHAIN_NAT)
    if _ipt("-t", "nat", "-A", IPT_CHAIN_NAT, "-s", AP_SUBNET, "-o", uplink,
            "-j", "MASQUERADE").returncode != 0:
        errs.append("nat rule")
    _ipt("-t", "nat", "-C", "POSTROUTING", "-j", IPT_CHAIN_NAT)
    if _ipt("-t", "nat", "-C", "POSTROUTING", "-j", IPT_CHAIN_NAT).returncode != 0:
        if _ipt("-t", "nat", "-I", "POSTROUTING", "1", "-j", IPT_CHAIN_NAT).returncode != 0:
            errs.append("postrouting jump")
    _ipt("-N", IPT_CHAIN_FWD)
    if _ipt("-A", IPT_CHAIN_FWD, "-i", uplink, "-o", ap, "-m", "conntrack",
            "--ctstate", "RELATED,ESTABLISHED", "-j", "ACCEPT").returncode != 0:
        errs.append("fwd return")
    if _ipt("-A", IPT_CHAIN_FWD, "-i", ap, "-o", uplink, "-j", "ACCEPT").returncode != 0:
        errs.append("fwd out")
    if _ipt("-C", "FORWARD", "-j", IPT_CHAIN_FWD).returncode != 0:
        if _ipt("-I", "FORWARD", "1", "-j", IPT_CHAIN_FWD).returncode != 0:
            errs.append("forward jump")
    return (False, "; ".join(errs)) if errs else (True, "")


def apply_nat(ap: str, uplink: str) -> tuple[bool, str]:
    if not uplink:
        return False, "no IPv4 default-route uplink to share"
    ok, why = _apply_nat_nft(ap, uplink)
    if ok:
        return True, ""
    ik, iwhy = _apply_nat_ipt(ap, uplink)
    if ik:
        return True, "nftables NAT unavailable (%s); used dedicated iptables chains" % why
    return False, "nft: %s; iptables: %s" % (why, iwhy)


def clear_nat() -> None:
    run(["/usr/sbin/nft", "delete", "table", "inet", TABLE])
    _ipt("-t", "nat", "-D", "POSTROUTING", "-j", IPT_CHAIN_NAT)
    _ipt("-t", "nat", "-F", IPT_CHAIN_NAT)
    _ipt("-t", "nat", "-X", IPT_CHAIN_NAT)
    _ipt("-D", "FORWARD", "-j", IPT_CHAIN_FWD)
    _ipt("-F", IPT_CHAIN_FWD)
    _ipt("-X", IPT_CHAIN_FWD)


def _read_pid(path: str) -> int:
    try:
        with open(path) as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def _alive(pid: int) -> bool:
    return pid > 0 and os.path.exists("/proc/%d" % pid)


def _kill_pid(path: str) -> None:
    pid = _read_pid(path)
    if _alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        for _ in range(30):
            if not _alive(pid):
                break
            time.sleep(0.1)


def stop(quiet: bool = False) -> dict:
    _kill_pid(RUN + "/hostapd.pid")
    _kill_pid(RUN + "/dnsmasq.pid")
    clear_nat()
    # find the AP interface from state and drop its address
    iface = ""
    try:
        with open(STATE) as f:
            iface = (json.load(f) or {}).get("interface") or ""
    except (OSError, ValueError):
        pass
    if iface and IFACE_RE.match(iface) and os.path.exists("/sys/class/net/" + iface):
        run(["/usr/sbin/ip", "addr", "flush", "dev", iface])
    try:
        os.replace(STATE, STATE + ".off")
    except OSError:
        pass
    if not quiet:
        log("stopped")
    return {"success": True, "enabled": False, "state": "off"}


def status() -> dict:
    ap_pid = _read_pid(RUN + "/hostapd.pid")
    dhcp_pid = _read_pid(RUN + "/dnsmasq.pid")
    doc = {"schema_version": 1, "supported": shutil.which("hostapd") is not None,
           "enabled": bool(_alive(ap_pid) and _alive(dhcp_pid)),
           "hostapd_pid": ap_pid if _alive(ap_pid) else None,
           "dnsmasq_pid": dhcp_pid if _alive(dhcp_pid) else None,
           "ssid": "", "interface": "", "address": AP_ADDRESS, "subnet": AP_SUBNET,
           "dhcp": "dnsmasq", "nat": "nftables nuxel_hotspot"}
    try:
        with open(STATE) as f:
            st = json.load(f) or {}
        doc["ssid"] = st.get("ssid", "")
        doc["interface"] = st.get("interface", "")
        doc["uplink"] = st.get("uplink", "")
    except (OSError, ValueError):
        pass
    doc["state"] = "on" if doc["enabled"] else "off"
    doc["ip_forward"] = (run(["/usr/sbin/sysctl", "-n",
                              "net.ipv4.ip_forward"]).stdout.strip() == "1")
    return doc


def start(ssid: str, password: str, interface: str | None = None) -> dict:
    ssid = (ssid or "").strip()
    password = password or ""
    if not SSID_RE.match(ssid):
        return {"success": False, "error": "SSID must be 1-32 printable characters",
                "error_code": "INVALID_SSID"}
    if not PSK_RE.match(password):
        return {"success": False, "error": "passphrase must be 8-63 printable characters",
                "error_code": "INVALID_PASSWORD"}
    if not shutil.which("hostapd"):
        return {"success": False, "error": "hostapd is not installed",
                "error_code": "HOSTAPD_MISSING"}
    if not shutil.which("dnsmasq"):
        return {"success": False, "error": "dnsmasq is not installed",
                "error_code": "DNSMASQ_MISSING"}
    uplink = _default_uplink()
    if not uplink:
        return {"success": False, "error": "no IPv4 default route to share",
                "error_code": "NO_UPLINK"}
    # Never take the owner's connected station interface away.
    ap, reason = _ap_capable_interface(interface)
    if not ap:
        return {"success": False, "error": reason or "no AP interface",
                "error_code": "NO_AP_INTERFACE"}
    if ap == uplink:
        return {"success": False, "error": "AP interface is the uplink",
                "error_code": "AP_IS_UPLINK"}
    ok, why = _phy_supports_ap(ap)
    if not ok:
        return {"success": False, "error": why, "error_code": "AP_UNSUPPORTED"}
    stop(quiet=True)
    # Without forwarding+dnsmasq there is no "sharing", only an AP island.
    run(["/usr/sbin/sysctl", "-qw", "net.ipv4.ip_forward=1"])
    os.makedirs(RUN, mode=0o755, exist_ok=True)
    os.makedirs(RUN + "/ctrl", mode=0o755, exist_ok=True)
    conf = write_hostapd_conf(ap, ssid, password)
    dconf = write_dnsmasq_conf(ap)
    run(["/usr/sbin/ip", "link", "set", ap, "down"])
    run(["/usr/sbin/ip", "addr", "replace", AP_CIDR, "dev", ap])
    proc = subprocess.run(["/usr/sbin/hostapd", "-B", "-P", RUN + "/hostapd.pid", conf],
                          capture_output=True, text=True, timeout=25)
    if proc.returncode != 0:
        clear_nat()
        return {"success": False, "error": "hostapd failed to start",
                "error_code": "HOSTAPD_FAILED",
                "detail": (proc.stderr or proc.stdout or "").strip()[:400]}
    dpid = subprocess.run(["/usr/sbin/dnsmasq", "--conf-file=" + dconf],
                          capture_output=True, text=True, timeout=15)
    if dpid.returncode != 0:
        _kill_pid(RUN + "/hostapd.pid")
        clear_nat()
        return {"success": False, "error": "dnsmasq failed to start",
                "error_code": "DNSMASQ_FAILED",
                "detail": (dpid.stderr or dpid.stdout or "").strip()[:400]}
    ok, why = apply_nat(ap, uplink)
    doc = {"schema_version": 1, "ssid": ssid, "interface": ap,
           "uplink": uplink, "address": AP_ADDRESS, "subnet": AP_SUBNET,
           "started_at": int(time.time()), "nat": ok, "nat_error": why}
    with open(STATE, "w") as f:
        json.dump(doc, f)
    if not ok:
        log("warning: NAT not applied: " + why)
    log("started ssid=%s iface=%s uplink=%s nat=%s" % (ssid, ap, uplink, ok))
    out = status()
    out["success"] = bool(out.get("enabled"))
    out["nat_applied"] = ok
    if why:
        out["nat_error"] = why
    return out


def main(argv) -> int:
    ap = argparse.ArgumentParser(prog="nuxel-hotspot")
    ap.add_argument("verb", choices=("start", "stop", "status"))
    ap.add_argument("--ssid", default="")
    ap.add_argument("--password", default="")
    ap.add_argument("--interface", default=None)
    ns = ap.parse_args(argv)
    if os.geteuid() != 0:
        print(json.dumps({"success": False, "error": "root required"}))
        return 1
    if ns.verb == "start":
        res = start(ns.ssid, ns.password, ns.interface)
    elif ns.verb == "stop":
        res = stop()
    else:
        res = status()
    print(json.dumps(res, indent=1))
    return 0 if res.get("success", True) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
