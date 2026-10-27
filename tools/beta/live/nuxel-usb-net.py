#!/usr/bin/env python3
"""nuxel-usb-net — opt-in USB CDC-NCM networking alongside the serial console.

Runs ON the phone as root.  It never flashes, rebuilds or reboots.  It only uses
the kernel's existing configfs NCM function, which the live 4.14.253 kernel
reports as compiled-in (CONFIG_USB_F_NCM=y / CONFIG_USB_CONFIGFS_NCM=y).

Safety model
------------
  * The existing ACM function is never removed.  NCM is an additional function
    in the same config, so serial remains part of the composite gadget.
  * Every change is recorded in a JSON backup.  --rollback restores the UDC,
    removes only the NCM link/function and removes only the reserved address.
  * --apply refuses without --i-understand-serial-may-reenumerate.
  * A detached rollback timer restores the previous gadget if --confirm is not
    run within --rollback-seconds.  The live console supervisor reopens ttyGS0
    when the gadget re-enumerates, but the timer does not rely on that.
  * No default route is changed and the Wi-Fi interface is never touched.
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nuxel_tri_link as tl  # noqa: E402

DEFAULT_GADGET = "/sys/kernel/config/usb_gadget/nuxel"
DEFAULT_STATE = "/var/lib/nuxel/usb-net"
DEFAULT_RUN = "/run"
USB_IP = "10.15.19.82/24"
USB_HOST_IP = "10.15.19.1/24"
USB_SUBNET = "10.15.19.0/24"
DEV_MAC = "02:6e:75:78:65:01"
HOST_MAC = "02:6e:75:78:65:02"

#: NUXEL-26000 physical result: on the live Samsung-derived 4.14.253 kernel the
#: configfs NCM attempt reached "Panic#2 Part1" and the watchdog rebooted the
#: phone.  This is a real hard blocker, not a test limitation.  The code remains
#: available for a future kernel, but apply refuses by default on this release.
KNOWN_BAD_NCM_KERNELS = {"4.14.253"}


class UsbNetError(Exception):
    pass


def _read(path) -> str:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return ""


def _write(path, value: str) -> None:
    Path(path).write_text(value)


def _run(cmd, check=False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _ip_state() -> dict:
    addr = _run(["ip", "-4", "-o", "addr", "show"]).stdout
    route = _run(["ip", "-4", "route", "show"]).stdout
    return {"addr": addr, "route": route}


def subnet_in_use(state: dict, subnet: str = USB_SUBNET) -> str | None:
    """Return the interface already owning the subnet, if any."""
    want = subnet.split("/")[0].rsplit(".", 1)[0] + "."
    for line in (state.get("route", "") + "\n" + state.get("addr", "")).splitlines():
        if want in line:
            m = re.search(r"\bdev\s+(\S+)", line)
            if m and m.group(1) not in ("usb0", "ncm0", "rndis0"):
                return m.group(1)
    return None


def snapshot(gadget: Path, state_dir: Path) -> dict:
    udc = _read(gadget / "UDC")
    functions = sorted(p.name for p in (gadget / "functions").iterdir()
                       if p.is_dir()) if (gadget / "functions").is_dir() else []
    links = sorted(p.name for p in (gadget / "configs").glob("*/[!.]*")
                   if p.is_symlink()) if (gadget / "configs").is_dir() else []
    doc = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "gadget": str(gadget),
        "udc": udc,
        "functions": functions,
        "links": links,
        "ncm_link": None,
        "ncm_function_created": False,
        "ip": _ip_state(),
        "usb_ip": USB_IP,
    }
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "backup.json").write_text(json.dumps(doc, indent=2, sort_keys=True))
    return doc


def _link_path(gadget: Path) -> Path:
    configs = sorted(p for p in (gadget / "configs").iterdir() if p.is_dir())
    if not configs:
        raise UsbNetError("gadget has no configuration directory")
    return configs[0] / "ncm.usb0"


def capability(gadget: Path, kernel_config: str,
               kernel_release: str | None = None,
               known_bad_kernels: set[str] | None = None) -> dict:
    cfg = tl.parse_kernel_config(kernel_config)
    release = kernel_release or os.uname().release
    bad = set(KNOWN_BAD_NCM_KERNELS if known_bad_kernels is None else known_bad_kernels)
    compiled = cfg.get("CONFIG_USB_F_NCM") == "y" and cfg.get("CONFIG_USB_CONFIGFS_NCM") == "y"
    udc = _read(gadget / "UDC")
    funcs = sorted(p.name for p in (gadget / "functions").iterdir()
                   if p.is_dir()) if (gadget / "functions").is_dir() else []
    link = None
    try:
        link = str(_link_path(gadget))
    except UsbNetError:
        pass
    net = Path("/sys/class/net")
    ifaces = sorted(p.name for p in net.iterdir()) if net.is_dir() else []
    return {
        "compiled_ncm": compiled,
        "gadget_present": gadget.is_dir(),
        "bound_udc": udc,
        "functions": funcs,
        "ncm_link": link,
        "has_ncm_function": "ncm.usb0" in funcs,
        "has_usb0": "usb0" in ifaces,
        "interfaces": ifaces,
        "kernel_release": release,
        "known_bad_kernel": release in bad,
        "blocked_reason": ("the live 4.14.253 NCM/configfs path panicked the kernel "
                           "(pstore Panic#2; watchdog reboot) during NUXEL-26000; "
                           "do not retry without a fixed kernel/gadget stack"
                           if release in bad else ""),
        "status": ("BLOCKED_KERNEL_PANIC" if release in bad else
                   ("AVAILABLE" if "usb0" in ifaces else
                    ("SUPPORTED_NOT_ENABLED" if compiled and gadget.is_dir() and udc else
                     "BLOCKED"))),
    }


def _rebind(gadget: Path, udc: str) -> None:
    _write(gadget / "UDC", "\n")
    time.sleep(0.4)
    _write(gadget / "UDC", udc + "\n")
    time.sleep(0.4)


def _wait_iface(name: str, seconds: float = 20.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if Path("/sys/class/net", name).exists():
            return True
        time.sleep(0.25)
    return False


def apply(gadget: Path, state_dir: Path, run_dir: Path, rollback_seconds: int,
          kernel_config: str, *, allow_serial_risk: bool,
          kernel_release: str | None = None,
          allow_unsafe_kernel: bool = False) -> dict:
    if not allow_serial_risk:
        raise UsbNetError("refusing --apply without --i-understand-serial-may-reenumerate")
    cap = capability(gadget, kernel_config, kernel_release=kernel_release)
    if cap["known_bad_kernel"] and not allow_unsafe_kernel:
        raise UsbNetError("BLOCKED_KERNEL_PANIC: %s (use --allow-unsafe-kernel only "
                          "for a deliberate experiment)" % cap["blocked_reason"])
    if not cap["compiled_ncm"]:
        raise UsbNetError("kernel lacks CONFIG_USB_F_NCM/CONFIG_USB_CONFIGFS_NCM")
    if not cap["gadget_present"] or not cap["bound_udc"]:
        raise UsbNetError("no bound Nuxel configfs gadget")
    if cap["has_usb0"]:
        return {"status": "ALREADY_AVAILABLE", "capability": cap}
    state = _ip_state()
    conflict = subnet_in_use(state)
    if conflict:
        raise UsbNetError("subnet %s is already in use on %s; refusing to change routing"
                          % (USB_SUBNET, conflict))
    backup = snapshot(gadget, state_dir)
    ncm = gadget / "functions" / "ncm.usb0"
    created = False
    linked = False
    try:
        if not ncm.is_dir():
            ncm.mkdir()
            created = True
        # Do not write ifname: on this kernel it is a read-only attribute
        # (0444) and writing it raised EACCES before the link existed.  The NCM
        # function creates usb0 by default.
        for name, value in (("dev_addr", DEV_MAC), ("host_addr", HOST_MAC)):
            p = ncm / name
            if p.exists() and os.access(p, os.W_OK):
                _write(p, value + "\n")
        link = _link_path(gadget)
        if not link.exists():
            os.symlink(ncm, link)
            linked = True
        backup["rebind_needed"] = True
        (state_dir / "backup.json").write_text(json.dumps(backup, indent=2, sort_keys=True))
        _rebind(gadget, backup["udc"])
        if not _wait_iface("usb0", 20):
            raise UsbNetError("usb0 did not appear after NCM bind; rolling back")
        _run(["ip", "addr", "add", USB_IP, "dev", "usb0"], check=False)
        _run(["ip", "link", "set", "usb0", "up"], check=False)
        got = _run(["ip", "-4", "-o", "addr", "show", "dev", "usb0"]).stdout
        if USB_IP.split("/")[0] not in got:
            raise UsbNetError("usb0 did not accept %s: %s" % (USB_IP, got.strip()))
        sshd = _run(["systemctl", "is-active", "sshd.service"]).stdout.strip()
        if sshd != "active":
            _run(["systemctl", "start", "sshd.service"], check=False)
            sshd = _run(["systemctl", "is-active", "sshd.service"]).stdout.strip()
        backup.update({"ncm_link": str(link), "ncm_function_created": created,
                       "usb0_created": True})
        (state_dir / "backup.json").write_text(json.dumps(backup, indent=2, sort_keys=True))
        confirmed = run_dir / "nuxel-usb-net.confirmed"
        try:
            confirmed.unlink()
        except OSError:
            pass
        timer = _arm_timer(state_dir, run_dir, rollback_seconds)
        doc = {
            "status": "APPLIED_UNCONFIRMED",
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "usb_ip": USB_IP,
            "host_ip": USB_HOST_IP,
            "sshd": sshd,
            "rollback_seconds": rollback_seconds,
            "timer_pid": timer,
            "capability": cap,
            "note": "run --confirm after SSH over USB works; otherwise the timer rolls back",
        }
        (state_dir / "status.json").write_text(json.dumps(doc, indent=2, sort_keys=True))
        return doc
    except BaseException:
        _rollback_from(gadget, state_dir, backup, run_dir)
        raise


def _arm_timer(state_dir: Path, run_dir: Path, seconds: int) -> int:
    script = Path(__file__).resolve()
    timer = subprocess.Popen(
        [sys.executable, str(script), "--timer", "--rollback-seconds", str(seconds),
         "--state-dir", str(state_dir), "--run-dir", str(run_dir)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    (state_dir / "timer.pid").write_text(str(timer.pid) + "\n")
    return timer.pid


def _kill_timer(state_dir: Path) -> None:
    try:
        pid = int((state_dir / "timer.pid").read_text().strip())
        os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    try:
        (state_dir / "timer.pid").unlink()
    except OSError:
        pass


def _rollback_from(gadget: Path, state_dir: Path, backup: dict, run_dir: Path) -> dict:
    errors = []
    try:
        _kill_timer(state_dir)
    except Exception as e:  # noqa: BLE001
        errors.append("timer: %s" % e)
    link = None
    if backup.get("ncm_link"):
        link = Path(backup["ncm_link"])
    else:
        try:
            link = _link_path(gadget)
        except UsbNetError:
            link = None
    if link is not None and link.is_symlink():
        try:
            link.unlink()
        except OSError as e:
            errors.append("unlink %s: %s" % (link, e))
    ncm = gadget / "functions" / "ncm.usb0"
    if backup.get("ncm_function_created") and ncm.is_dir():
        try:
            ncm.rmdir()
        except OSError as e:
            errors.append("rmdir %s: %s" % (ncm, e))
    udc = backup.get("udc")
    # Only rebind when this attempt actually changed/rebound the UDC.  An early
    # failure (e.g. an unwritable attribute before the link) must leave the live
    # ACM gadget alone: NUXEL-26000 measured that an unnecessary rebind left the
    # host unable to SET_CONFIGURATION and ended in a kernel panic/watchdog.
    if udc and backup.get("rebind_needed"):
        try:
            _rebind(gadget, udc)
        except OSError as e:
            errors.append("rebind: %s" % e)
    _run(["ip", "addr", "del", USB_IP, "dev", "usb0"], check=False)
    try:
        (run_dir / "nuxel-usb-net.confirmed").unlink()
    except OSError:
        pass
    doc = {"status": "ROLLED_BACK" if not errors else "ROLLBACK_INCOMPLETE",
           "errors": errors,
           "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    try:
        (state_dir / "status.json").write_text(json.dumps(doc, indent=2, sort_keys=True))
    except OSError:
        pass
    return doc


def rollback(gadget: Path, state_dir: Path, run_dir: Path) -> dict:
    try:
        backup = json.loads((state_dir / "backup.json").read_text())
    except (OSError, ValueError) as e:
        raise UsbNetError("no usable backup: %s" % e)
    return _rollback_from(gadget, state_dir, backup, run_dir)


def confirm(state_dir: Path, run_dir: Path) -> dict:
    _kill_timer(state_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "nuxel-usb-net.confirmed").write_text(
        time.strftime("%Y-%m-%dT%H:%M:%S%z") + "\n")
    doc = {"status": "CONFIRMED", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (state_dir / "status.json").write_text(json.dumps(doc, indent=2, sort_keys=True))
    return doc


def status(gadget: Path, state_dir: Path, run_dir: Path, kernel_config: str) -> dict:
    doc = capability(gadget, kernel_config)
    doc["confirmed"] = (run_dir / "nuxel-usb-net.confirmed").exists()
    for name in ("backup.json", "status.json"):
        try:
            doc[name] = json.loads((state_dir / name).read_text())
        except (OSError, ValueError):
            doc[name] = None
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description="opt-in USB CDC-NCM alongside the serial console")
    ap.add_argument("--gadget", default=DEFAULT_GADGET)
    ap.add_argument("--state-dir", default=DEFAULT_STATE)
    ap.add_argument("--run-dir", default=DEFAULT_RUN)
    ap.add_argument("--kernel-config", default="/proc/config.gz")
    ap.add_argument("--rollback-seconds", type=int, default=120)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--timer", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--i-understand-serial-may-reenumerate", action="store_true")
    ap.add_argument("--allow-unsafe-kernel", action="store_true",
                    help="EXPERIMENT ONLY: override the known-bad 4.14.253 block")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    gadget = Path(args.gadget)
    state_dir = Path(args.state_dir)
    run_dir = Path(args.run_dir)
    kernel = tl.read_kernel_config(args.kernel_config)
    try:
        if args.timer:
            time.sleep(max(1, args.rollback_seconds))
            if not (run_dir / "nuxel-usb-net.confirmed").exists():
                rollback(gadget, state_dir, run_dir)
            return 0
        if args.confirm:
            doc = confirm(state_dir, run_dir)
        elif args.rollback:
            doc = rollback(gadget, state_dir, run_dir)
        elif args.apply:
            doc = apply(gadget, state_dir, run_dir, args.rollback_seconds, kernel,
                        allow_serial_risk=args.i_understand_serial_may_reenumerate,
                        allow_unsafe_kernel=args.allow_unsafe_kernel)
        else:
            doc = status(gadget, state_dir, run_dir, kernel)
    except (UsbNetError, OSError) as e:
        print("!! %s" % e, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    else:
        print("# usb-net: %s" % doc.get("status"))
        for k in ("compiled_ncm", "bound_udc", "functions", "has_usb0",
                  "rollback_seconds", "timer_pid", "errors"):
            if k in doc:
                print("# %s: %s" % (k, doc[k]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
