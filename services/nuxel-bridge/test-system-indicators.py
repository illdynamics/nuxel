#!/usr/bin/env python3
"""Offline acceptance tests for the three independent lockhead indicators.

No device, no root, no D-Bus.  A synthetic /sys, /proc and /run tree is built so
the exact states that are hard to reproduce on a desk can all be proven:

  * every reachable on/off combination is independent (the console is
    deliberately unreachable without a USB data link);
  * a charging-only cable never produces a PC connection;
  * root access alone never produces a live console;
  * a bound gadget with no running console process is NOT a console;
  * only configured UDC state is data; addressed/not-attached are not;
  * Full/Not-charging are external power but not active charging.
"""
from __future__ import annotations

import importlib.util
import itertools
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.join(HERE, "src", "system_indicators.py")
spec = importlib.util.spec_from_file_location("system_indicators", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


class FakeSystem:
    def __init__(self) -> None:
        self.root = tempfile.mkdtemp(prefix="nuxel-indicators-")
        self.ps = os.path.join(self.root, "power_supply")
        self.udc = os.path.join(self.root, "udc")
        self.tty = os.path.join(self.root, "tty")
        self.gadget = os.path.join(self.root, "usb_gadget")
        self.proc = os.path.join(self.root, "proc")
        self.run = os.path.join(self.root, "run")
        self.android_usb = os.path.join(self.root, "android_usb")
        self.typec = os.path.join(self.root, "typec")
        self.debugfs = os.path.join(self.root, "debugfs")
        for path in (self.ps, self.udc, self.tty, self.gadget, self.proc,
                     self.android_usb, self.typec, self.debugfs,
                     os.path.join(self.run, "nuxel")):
            os.makedirs(path, exist_ok=True)
        os.environ.update({
            "NUXEL_SYS_POWER_SUPPLY": self.ps,
            "NUXEL_SYS_UDC": self.udc,
            "NUXEL_SYS_TTY": self.tty,
            "NUXEL_CONFIGFS_GADGET": self.gadget,
            "NUXEL_PROC": self.proc,
            "NUXEL_RUN": self.run,
            "NUXEL_CONSOLE_TTY": "ttyGS0",
            "NUXEL_ANDROID_USB_STATE": os.path.join(self.android_usb, "state"),
            "NUXEL_SYS_TYPEC": self.typec,
            "NUXEL_DEBUGFS": self.debugfs,
        })

    def write(self, rel: str, value: str) -> None:
        full = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(value)

    def link(self, rel: str, target: str) -> None:
        full = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if os.path.lexists(full):
            os.unlink(full)
        os.symlink(target, full)

    def battery(self, status: str, capacity: str = "71") -> None:
        self.write("power_supply/battery/type", "Battery")
        self.write("power_supply/battery/capacity", capacity)
        self.write("power_supply/battery/status", status)

    def usb_power(self, online: str) -> None:
        self.write("power_supply/usb/type", "USB")
        self.write("power_supply/usb/online", online)

    def bind_gadget(self, state: str | None) -> None:
        self.write("usb_gadget/nuxel/UDC", "10c00000.dwc3")
        if state is not None:
            self.write("udc/10c00000.dwc3/state", state + "\n")

    def unbind_gadget(self) -> None:
        self.write("usb_gadget/nuxel/UDC", "\n")

    def console_process(self, pid: int = 4242, tty: bool = True,
                        command: str = "/opt/nuxel/nuxel-console /newroot") -> None:
        base = "proc/%d" % pid
        self.write(base + "/cmdline", command.replace(" ", "\0") + "\0")
        if tty:
            self.link(base + "/fd/0", "/dev/ttyGS0")

    def remove_console_process(self, pid: int = 4242) -> None:
        shutil.rmtree(os.path.join(self.proc, str(pid)), ignore_errors=True)


    def typec_role(self, role: str | None) -> None:
        """role=None removes the Type-C class (absent); otherwise writes the
        port0/data_role string (brackets mark the resolved role)."""
        path = os.path.join(self.typec, "port0")
        if role is None:
            shutil.rmtree(self.typec, ignore_errors=True)
            os.makedirs(self.typec, exist_ok=True)
            return
        os.makedirs(path, exist_ok=True)
        self.write("typec/port0/data_role", role + "\n")

    def dwc3_link(self, state: str | None) -> None:
        path = os.path.join(self.debugfs, "10c00000.dwc3")
        if state is None:
            shutil.rmtree(self.debugfs, ignore_errors=True)
            os.makedirs(self.debugfs, exist_ok=True)
            return
        os.makedirs(path, exist_ok=True)
        self.write("debugfs/10c00000.dwc3/link_state", state + "\n")

    def tty_registered(self, present: bool = True) -> None:
        path = os.path.join(self.tty, "ttyGS0", "dev")
        if present:
            self.write("tty/ttyGS0/dev", "254:0\n")
        elif os.path.exists(path):
            os.unlink(path)

    def reset(self) -> None:
        for name in os.listdir(self.root):
            path = os.path.join(self.root, name)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.unlink(path)
        for path in (self.ps, self.udc, self.tty, self.gadget, self.proc,
                     self.android_usb, self.typec, self.debugfs,
                     os.path.join(self.run, "nuxel")):
            os.makedirs(path, exist_ok=True)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def state() -> tuple:
    ind = mod.get_indicators()
    return (
        bool(ind["charging"]["external_power"]),
        bool(ind["charging"]["charging"]),
        bool(ind["usb_data"]["pc_connected"]),
        bool(ind["live_console"]["active"]),
    )


def main() -> int:
    fake = FakeSystem()
    try:
        # 1. Nothing connected: every indicator dimmed, honest sources.
        ind = mod.get_indicators()
        check(state() == (False, False, False, False), "empty system: all indicators off")
        check(ind["charging"]["source"].startswith("unavailable:"),
              "empty system: charging source is unavailable, not a assumed value")
        check(ind["usb_data"]["source"].startswith("unavailable:"),
              "empty system: USB source is unavailable")

        # 2. Charging-only cable. This is the explicit false-PC test.
        fake.battery("Discharging")
        fake.usb_power("1")
        check(state() == (True, False, False, False),
              "charging-only cable: power on, NOT charging, NO PC, NO console")

        # 3. Actively charging.
        fake.battery("Charging")
        check(state() == (True, True, False, False),
              "actively charging: power + charging only")

        # 3b. OTG / USB host mode is not charging.
        fake.reset()
        fake.battery("Discharging")
        fake.write("power_supply/otg/type", "OTG\n")
        fake.write("power_supply/otg/online", "1\n")
        ind = mod.get_indicators()
        check(ind["charging"]["external_power"] is False,
              "OTG/host mode does NOT light the charging indicator")

        # 4. Full / not charging are still externally powered.
        fake.reset()
        fake.battery("Full")
        fake.usb_power("1")
        check(state() == (True, False, False, False),
              "battery Full: external power on, not actively charging")
        fake.battery("Not charging")
        check(state() == (True, False, False, False),
              "battery Not charging: external power on, not active charging")

        # 5. Data link without any console process: PC yes, console no.
        fake.battery("Charging")
        fake.bind_gadget("configured")
        fake.tty_registered(True)
        check(state() == (True, True, True, False),
              "configured UDC + tty but no console process: PC only")

        # 6. Real console process (tty fd held) plus configured link: all three.
        fake.console_process(pid=4242, tty=True)
        check(state() == (True, True, True, True),
              "configured UDC + running console process: all three active")
        ind = mod.get_indicators()
        check(ind["live_console"]["pids"] == [4242],
              "console process pid is reported")
        check(ind["live_console"]["source"].startswith("proc:nuxel-console"),
              "console source names the process/tty evidence")

        # Address assignment precedes configuration and is not proof that a
        # host accepted a data function.  The console icon is gated by a real
        # data link (A71), so it must fall with the PC indicator.
        fake.bind_gadget("addressed")
        check(state() == (True, True, False, False),
              "addressed UDC is pre-enumeration: PC and console stay off")
        fake.bind_gadget("configured")

        # 7. Root shell alone is not a live console: no nuxel-console process.
        fake.remove_console_process(4242)
        fake.console_process(pid=4343, tty=True, command="/bin/sh")
        check(state() == (True, True, True, False),
              "root shell alone (not nuxel-console) does NOT light live console")

        # 8. Console process exists but its tty is not open: inactive.
        fake.remove_console_process(4343)
        fake.console_process(pid=4444, tty=False)
        check(state() == (True, True, True, False),
              "nuxel-console with no console tty fd does NOT light live console")
        fake.remove_console_process(4444)

        # 9. Gadget bound but not attached to a host: no PC, and therefore no
        #    live USB console either -- the session cannot outlive the link.
        fake.bind_gadget("not attached")
        fake.console_process(pid=4545, tty=True)
        ind = mod.get_indicators()
        check(state() == (True, True, False, False),
              "not-attached UDC: console cannot stay active without a data link")
        check(ind["live_console"]["source"] == "inactive:no-usb-data-link",
              "detached console reports the missing USB data link")
        fake.remove_console_process(4545)

        # 10. Console process alive but gadget gone: do not keep a stale "on".
        fake.unbind_gadget()
        fake.console_process(pid=4646, tty=True)
        check(state() == (True, True, False, False),
              "console process without a bound gadget is not an active session")
        fake.remove_console_process(4646)

        # 11. Session lease from the console implementation (stores pid).
        fake.bind_gadget("configured")
        fake.write("run/nuxel/live-console-session", "pid=4747\n")
        fake.write("proc/4747/cmdline", "/opt/nuxel/nuxel-console\0/newroot\0")
        check(state() == (True, True, True, True),
              "validated session lease + live pid lights the console")
        check(mod.get_indicators()["live_console"]["source"] ==
              "lease:nuxel-console:serving",
              "serving lease source is reported as the console lease")
        fake.write("run/nuxel/live-console-session", "pid=999999\n")
        check(state() == (True, True, True, False),
              "stale/dead lease pid does NOT light the console")

        # A live PID that is NOT nuxel-console must not satisfy a stale lease.
        fake.write("run/nuxel/live-console-session", "pid=4748\n")
        fake.write("proc/4748/cmdline", "/bin/sh\0")
        check(state() == (True, True, True, False),
              "lease for a non-console live PID does NOT light the console")

        # A lease is bound to the process generation, not just a reusable PID.
        fake.write("proc/4747/stat", "4747 (nuxel-console) S 1 4747 4747 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 777 0 0\n")
        fake.write("run/nuxel/live-console-session",
                   "pid=4747\nstate=serving\nstart_ticks=777\n")
        check(state() == (True, True, True, True),
              "start_ticks-bound serving lease lights the console")
        fake.write("run/nuxel/live-console-session",
                   "pid=4747\nstate=serving\nstart_ticks=778\n")
        check(state() == (True, True, True, False),
              "reused PID with the wrong start_ticks is rejected")
        fake.write("run/nuxel/live-console-session",
                   "pid=4747\nstate=stopped\n")
        check(state() == (True, True, True, False),
              "a non-serving lease state does not light the console")
        fake.write("run/nuxel/live-console-session", "pid=4747\n")

        # 11b. Vendor USB_STATE can be stale after detach.  Without a bound,
        # configured UDC it is diagnostic only and must fail closed.
        fake.reset()
        fake.battery("Charging")
        fake.usb_power("1")
        fake.write("android_usb/state", "CONFIGURED\n")
        check(state() == (True, True, False, False),
              "stale android USB CONFIGURED without UDC proof: PC stays off")
        fake.write("android_usb/state", "DISCONNECTED\n")
        check(state() == (True, True, False, False),
              "android USB state DISCONNECTED is not a PC connection")

        fake.bind_gadget(None)
        fake.write("android_usb/state", "CONFIGURED\n")
        check(state() == (True, True, False, False),
              "bound gadget plus vendor CONFIGURED but no UDC state: PC stays off")

        # 11c. PHYSICAL DETACH VETO (A73/A74): a stale UDC "configured" must not
        #      survive the independent Type-C data_role down signal.
        fake.reset()
        fake.battery("Charging")
        fake.usb_power("1")
        fake.bind_gadget("configured")
        fake.typec_role("host [device]")
        check(state() == (True, True, True, False),
              "configured UDC + typec [device] role: PC on")

        fake.typec_role("host device")  # no bracket: role not resolved to device
        check(state() == (True, True, False, False),
              "typec no-device-role vetoes a stale configured UDC")

        fake.typec_role("host [device]")
        check(state() == (True, True, True, False),
              "typec [device] role restored: PC on again")

        # Absent Type-C class is neutral (desktop / no Type-C kernels).
        fake.typec_role(None)
        check(state() == (True, True, True, False),
              "absent Type-C class leaves UDC proof authoritative")

        # A74 REGRESSION: the DWC3 debugfs link_state must NOT be consulted at
        # all.  A synthetic debugfs "Off" node exists but must have no effect —
        # proving the dangerous debugfs register read was removed from the
        # detach-veto path (it hard-locks-up the downstream 4.14 kernel after
        # detach; see the module docstring in system_indicators.py).
        fake.typec_role("host [device]")
        fake.dwc3_link("Off")
        check(state() == (True, True, True, False),
              "A74: dwc3 debugfs link_state is NOT read; PC stays on when "
              "Type-C role is device")
        fake.dwc3_link(None)

        # 12. Prove the state space matches the A71 truth table.  Charging is
        #     independent; the console is only reachable while a data link is
        #     present, so "live without PC" must collapse to live=off.
        combinations = set()
        for power, pc, live in itertools.product((False, True), repeat=3):
            fake.reset()
            if power:
                fake.battery("Charging")
                fake.usb_power("1")
            else:
                fake.battery("Discharging")
                fake.usb_power("0")
            if live:
                fake.bind_gadget("configured" if pc else "not attached")
                fake.tty_registered(True)
                fake.console_process(pid=5000, tty=True)
            elif pc:
                fake.bind_gadget("configured")
            else:
                fake.unbind_gadget()
            combined = state()
            want_live = live and pc
            combinations.add((combined[0], combined[2], combined[3]))
            check(combined == (power, power, pc, want_live),
                  "combination power=%d pc=%d live=%d -> %s"
                  % (power, pc, live, combined))
        check(len(combinations) == 6,
              "the six reachable indicators combinations are distinct")
    finally:
        fake.cleanup()

    print("\n" + ("ALL PASS" if not FAILURES else "%d FAILURES" % len(FAILURES)))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
