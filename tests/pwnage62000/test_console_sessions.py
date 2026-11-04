#!/usr/bin/env python3
"""PWNAGE-62000: proven interactive WLAN SSH session model.

Builds a synthetic /proc tree (socket inode -> sshd -> nuxel shell -> /dev/pts)
and proves that readiness/listeners/port-forwards/one-shot commands never light
the WLAN console icon, while real PTY sessions do and close promptly.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODULE = ROOT / "services/nuxel-bridge/src/system_indicators.py"
spec = importlib.util.spec_from_file_location("system_indicators_p62000", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAIL = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


class FakeProc:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="p62000-proc-"))
        (self.root / "net").mkdir(parents=True)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def link(self, rel, target):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() or p.is_symlink():
            p.unlink()
        p.symlink_to(target)

    def tcp_line(self, local_hex="101E140A", inode=1234, state="01"):
        return ("  0: %s:0016 0A141E0A:1234 %s 00000000:00000000 00:00000000 "
                "00000000 0 0 %d 1 00000000 20 4 30 10 -1\n"
                % (local_hex, state, inode))

    def net(self, lines, proto="tcp"):
        self.write("net/%s" % proto,
                   "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when "
                   "retrnsmt   uid  timeout inode\n" + "".join(lines))

    def proc(self, pid, comm, ppid=1, uid=0, pty=None, socket_inode=None,
             start_ticks=777, cmdline=None):
        self.write("%d/comm" % pid, comm + "\n")
        self.write("%d/cmdline" % pid,
                   (cmdline if cmdline is not None else comm) + "\x00")
        self.write("%d/stat" % pid,
                   "%d (%s) S %d 1 1 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 %d 0 0\n"
                   % (pid, comm, ppid, start_ticks))
        self.write("%d/status" % pid, "Name:\t%s\nUid:\t%d\t%d\t%d\t%d\n"
                   % (comm, uid, uid, uid, uid))
        if pty:
            self.link("%d/fd/0" % pid, pty)
        if socket_inode:
            self.link("%d/fd/3" % pid, "socket:[%d]" % socket_inode)

    def ssh_session(self, base_pid=100, inode=1234, wifi="10.20.30.16",
                    pty=True, uid=1000, shell="bash", state="01",
                    cmdline=None):
        self.net([self.tcp_line(inode=inode, state=state)])
        self.proc(base_pid, "sshd-session", uid=0, socket_inode=inode)
        self.proc(base_pid + 1, shell, ppid=base_pid, uid=uid,
                  pty=("/dev/pts/1" if pty else None), cmdline=cmdline)


def main():
    f = FakeProc()
    try:
        # Wi-Fi up + sshd listener + no sessions: availability is not activity.
        f.net([f.tcp_line(inode=0, state="0A")])
        check(mod.wlan_console_sessions(str(f.root), ["10.20.30.16"]) == [],
              "idle sshd listener is not a WLAN console session")

        # A port-forward / one-shot command has a socket but no shell/pty.
        f.net([f.tcp_line(inode=22)])
        f.proc(200, "sshd-session", uid=0, socket_inode=22)
        check(mod.wlan_console_sessions(str(f.root), ["10.20.30.16"]) == [],
              "established socket without an interactive shell/pty is not a console")

        # One real session.
        f.ssh_session(300, 333)
        one = mod.wlan_console_sessions(str(f.root), ["10.20.30.16"])
        check(len(one) == 1 and one[0]["interactive"] is True,
              "established socket + sshd + nuxel shell + pty is one session")
        check(one[0]["local_ip"] == "10.20.30.16" and one[0]["user"] == "nuxel",
              "session is attributed to the Wi-Fi local address and nuxel user")

        # Wrong local interface is not WLAN.
        check(mod.wlan_console_sessions(str(f.root), ["10.99.99.99"]) == [],
              "a socket on another local address is not labelled WLAN")

        # No pty is not interactive.
        f2 = FakeProc()
        try:
            f2.ssh_session(400, 444, pty=False)
            check(mod.wlan_console_sessions(str(f2.root), ["10.20.30.16"]) == [],
                  "SSH without a pty never counts as a console session")
        finally:
            f2.close()

        # Non-nuxel shell is not the approved console account.
        f3 = FakeProc()
        try:
            f3.ssh_session(500, 555, uid=0)
            check(mod.wlan_console_sessions(str(f3.root), ["10.20.30.16"]) == [],
                  "a root shell is not the approved console account")
        finally:
            f3.close()

        # A PTY alone is not enough: `ssh -t host true` runs a shell -c command.
        f6 = FakeProc()
        try:
            f6.ssh_session(700, 777, pty=True,
                           cmdline="/bin/bash -c true")
            check(mod.wlan_console_sessions(str(f6.root), ["10.20.30.16"]) == [],
                  "PTY + shell -c one-shot command is not an interactive console")
        finally:
            f6.close()

        # Two sessions, close one, close final.
        f4 = FakeProc()
        try:
            f4.net([f4.tcp_line(inode=601), f4.tcp_line(inode=602)])
            f4.proc(600, "sshd-session", uid=0, socket_inode=601)
            f4.proc(601, "bash", ppid=600, uid=1000, pty="/dev/pts/1")
            f4.proc(610, "sshd-session", uid=0, socket_inode=602)
            f4.proc(611, "zsh", ppid=610, uid=1000, pty="/dev/pts/2")
            check(len(mod.wlan_console_sessions(str(f4.root), ["10.20.30.16"])) == 2,
                  "two interactive Wi-Fi SSH sessions count as two")
            f4.net([f4.tcp_line(inode=601)])
            check(len(mod.wlan_console_sessions(str(f4.root), ["10.20.30.16"])) == 1,
                  "closing one of two sessions leaves one active")
            f4.net([])
            check(len(mod.wlan_console_sessions(str(f4.root), ["10.20.30.16"])) == 0,
                  "closing the last session removes WLAN activity")
        finally:
            f4.close()

        # Malformed state never fabricates a session.
        f5 = FakeProc()
        try:
            f5.write("net/tcp", "garbage\n")
            check(mod.wlan_console_sessions(str(f5.root), ["10.20.30.16"]) == [],
                  "malformed /proc/net/tcp yields no false active session")
        finally:
            f5.close()

        # Transport readiness and activity stay distinct.
        old_facts = mod._cached_tri_link_facts
        old_sessions = mod.wlan_console_sessions
        try:
            mod._cached_tri_link_facts = lambda: {"wifi_status": "AVAILABLE",
                                                  "usb_status": "BLOCKED_KERNEL_PANIC"}
            mod.wlan_console_sessions = lambda *a, **k: []
            tr = mod.console_transports({
                "active": True, "service_armed": True,
                "usb_session_active": False, "source": "service:armed", "pids": [],
            })
            check(tr["wlan"]["available"] is True and tr["wlan"]["active"] is False,
                  "Wi-Fi availability true with zero sessions: WLAN active false")
            check(tr["wlan"]["sessions"] == 0,
                  "idle readiness reports sessions=0")
            check(tr["serial"]["active"] is False,
                  "armed background service does not light the USB serial icon")
            mod.wlan_console_sessions = lambda *a, **k: [
                {"inode": 1, "shell_pid": 2, "interactive": True, "transport": "wlan"}]
            tr = mod.console_transports({
                "active": True, "service_armed": True,
                "usb_session_active": False, "source": "service:armed", "pids": [],
            })
            check(tr["wlan"]["active"] is True and tr["wlan"]["sessions"] == 1,
                  "one proven interactive session lights WLAN activity")
        finally:
            mod._cached_tri_link_facts = old_facts
            mod.wlan_console_sessions = old_sessions
    finally:
        f.close()

    print("\n" + ("ALL PASS" if not FAIL else "%d FAILURES" % len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
