#!/usr/bin/env python3
"""PWNAGE-62000 source/contract regressions for shell chrome and lock policy."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAIL = []


def read(rel):
    return (ROOT / rel).read_text()


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def main():
    session = read("tools/s10plus/a45/nuxel-session.sh")
    supervisor = read("tools/s10plus/a45/nuxel-shell-chrome.sh")
    navdock = read("tools/s10plus/a45/nuxel-navdock.c")
    statusbar = read("tools/s10plus/a45/nuxel-statusbar.c")
    host = read("tools/s10plus/a45/nuxel-pwa-host.c")
    ft = read("tools/s10plus/a59/nuxel-foreign-toplevel.c")
    builder = read("images/s10plus/build-phone-rootfs-inside-fedora.sh")
    wayland_stop = read("services/nuxel-s10/bin/nuxel-wayland-stop.sh")
    wlfb_hold = read("services/nuxel-s10/bin/nuxel-wl-fb-hold.sh")
    wayland_dropin = read("services/nuxel-s10/systemd/nuxel-wayland.service.d/40-bounded-stop.conf")
    wlfb_dropin = read("services/nuxel-s10/systemd/nuxel-wl-fb.service.d/25-reboot-hold.conf")
    audio_dropin = read("services/nuxel-s10/systemd/nuxel-audio-session.service.d/10-stop-bound.conf")
    audio_stop = read("services/nuxel-s10/bin/nuxel-audio-stop.sh")

    check("nuxel-shell-chrome.sh" in session and "nuxel-statusbar" not in session.split("starting supervised shell chrome")[1][:600],
          "session starts exactly one supervised chrome owner (no raw statusbar launch)")
    check("nuxel-navdock" in supervisor and "nuxel-statusbar" in supervisor and
          "watch-lock" in supervisor,
          "supervisor owns navdock, native top bar and lock watcher")
    check('if [ ! -x /usr/lib/nuxel/nuxel-statusbar ]' in supervisor,
          "missing native bar degrades to the Home DOM bar instead of crashing the session")

    check("watch-lock" in ft and "LOCK_RECEIPT" in ft and "FOREGROUND_STATE" in ft,
          "foreign-toplevel implements persistent lock enforcement + foreground state")
    check('{ "capabilities", "u", NULL }' in ft and
          '2, wl_seat_events' in ft,
          "wl_seat declaration consumes capabilities/name events")
    check("/* unknown -> fail closed */" in ft and
          "if (locked != 0)" in ft and "enforce_locked(1);" in ft,
          "lock watcher treats unknown/missing state as locked (fail closed)")
    check("_marshal(w->handle, 9" in ft and "_marshal(w->handle, 0" in ft,
          "lock enforcement un-fullscreens apps and raises/maximizes Home")
    check("case 0: w->maximized=1" in ft and "case 2: w->activated=1" in ft and
          "case 3: w->fullscreen=1" in ft,
          "foreign-toplevel state enum uses protocol values 0..3")
    check(", NULL, handle_version" in ft and
          ", &fto_handle_interface, handle_version" not in ft,
          "regular handle requests pass a NULL new-id interface to libwayland")
    check('open("/dev/fb0' not in ft and 'open("/dev/fb0' not in supervisor and
          'open("/dev/fb0' not in statusbar,
          "chrome/lock clients never open the framebuffer")

    check("dock_tick" in navdock and "NAV_DOCK_LOCK_RESTORE" in navdock,
          "navdock reconciles authoritative lock state on a bounded timer")
    check("last_st" in navdock and "last_home" in navdock and
          'publish_state("tick")' in navdock,
          "navdock republishes readiness/lock state on transitions")
    check("REQ_FILE" in navdock and "cmd_read_pending" in navdock,
          "navdock consumes a queued show/hide command when the FIFO was absent")
    check("publish_state" in navdock and "NAV_DOCK_SHOW_REFUSED" in navdock,
          "navdock publishes a readiness state and refuses show while locked")
    check("publish_state" in statusbar and "foreground_from_watcher" in statusbar,
          "native top bar publishes state and prefers the persistent foreground watcher")
    check('bar_hide();' in statusbar and 'preloading_active()' in statusbar,
          "native top bar hides on lock/Home/Home-preload and late layer closure")
    check("BAR_STRIP_INPUT_HEIGHT" in statusbar and "strip_mode" in statusbar and
          "bar_revealed" in statusbar and "touch_down" in statusbar,
          "native top bar bounds its touch band to the strip/reveal state")
    check("STATUSBAR_HIDDEN reason=lock_or_home" in statusbar,
          "existing lock/home hide receipt remains intact")

    check("nav_command" in host and "nuxel-navdock.request" in host,
          "host retries nav commands and queues them before the FIFO exists")
    check("request_authoritative_lock" in host and "screen-lock" in host,
          "host-native lock requests the authoritative bridge state")
    _sl = host.split('if (!strcmp(action, "screen-lock"))', 1)[1].split('return;', 1)[0]
    check('dprintf(fd, "screen-off\\n")' in _sl and
          "detail:{action:'lock'}" in _sl,
          "host screen-lock blanks the panel and drives the DOM lockscreen")
    check("int serial_active = ind_live_console();" in host and
          "int live = armed || serial_active" in host and
          "ind_wlan_ssh_sessions" in host,
          "native host separates base readiness from USB/WLAN session activity")
    check("ind_pid_has_socket_inode" in host and "ind_interactive_descendant" in host,
          "native WLAN indicator requires socket inode + interactive PTY descendant")

    check('install -m 0755 "$B/nuxel-statusbar"          "$STAGE/usr/lib/nuxel/nuxel-statusbar"' in builder,
          "image build installs the native top bar at the executable path")
    check("nuxel-statusbar.disabled" not in builder,
          "image build no longer disables the native top bar")
    check("nuxel-shell-chrome.sh" in builder and "nuxel-security-lock-rpc" in builder,
          "image build packages the supervisor and lock RPC helper")
    check("30-fast-stop.conf" in builder and "40-bounded-stop.conf" in builder,
          "image build installs the measured wayland stop drop-ins")
    check("25-reboot-hold.conf" in builder,
          "image build installs the bounded wl-fb reboot hold")

    check("cgroup.procs" in wayland_stop and "signal_all TERM" in wayland_stop and
          "signal_all KILL" in wayland_stop,
          "wayland stop signals the unit cgroup and has a bounded KILL fallback")
    check("kill -9 1" not in wayland_stop and "reboot -f" not in wayland_stop,
          "stop helper contains no forced reboot path")
    check("TimeoutStopSec=2" in wayland_dropin and "ExecStop=/usr/lib/nuxel/nuxel-wayland-stop.sh" in wayland_dropin,
          "wayland drop-in uses the bounded unit-specific stop helper")
    check("/run/nuxel/reboot-request" in wlfb_hold and "sleep 2" in wlfb_hold,
          "display bridge holds its last frame only for an owner-requested reboot")
    check("ExecStop=/usr/lib/nuxel/nuxel-wl-fb-hold.sh" in wlfb_dropin,
          "wl-fb reboot hold is wired as an ExecStop")
    check("TimeoutStopSec=2" in audio_dropin and
          "ExecStop=/usr/lib/nuxel/nuxel-audio-stop.sh" in audio_dropin and
          "cgroup.procs" in audio_stop and "signal_all TERM" in audio_stop and
          "signal_all KILL" in audio_stop,
          "audio-session stop is unit-specific and bounded")
    check("kill -9 1" not in audio_stop and "reboot -f" not in audio_stop,
          "audio stop helper contains no forced reboot path")

    print("\n" + ("ALL PASS" if not FAIL else "%d FAILURES" % len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
