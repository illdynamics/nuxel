#!/usr/bin/env python3
"""nuxel-browser-native — a genuine, top-level WebKitGTK browser for Nuxel.

Uses GTK3 + WebKit2GTK 4.1, the same stack the working nuxel-pwa-host launcher
uses on this device (GTK3/WebKit2-4.1 typelibs verified present; the GTK4
WebKit-6.0 web process does not spawn under this vendor 4.14 kernel).

Real WebKitWebView top-level navigation (NOT an iframe); TLS errors fail closed.

A68: exposes a control FIFO (/run/nuxel-browser.cmd) so the system shell can
drive in-app Back (browser history) before the app is backgrounded to Home.
State (uri/title/can_go_back/can_go_forward) is published to
/run/nuxel-browser.state for the bridge's back contract.
"""
import os
import sys
import json
import subprocess
import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2, GLib

STATE_PATH = "/run/nuxel-browser.state"
CTRL_FIFO = "/run/nuxel-browser.cmd"

def status_text():
    """Compact system status for the native surface (no invented state)."""
    try:
        wifi = open("/sys/class/net/wlan0/operstate").read().strip()
    except OSError:
        wifi = "unknown"
    battery = "?"
    for name in ("battery", "bq27541-0", "max77865-charger"):
        try:
            battery = open("/sys/class/power_supply/%s/capacity" % name).read().strip() + "%"
            break
        except OSError:
            continue
    return "%s  ·  Wi-Fi %s  ·  Battery %s" % (time.strftime("%H:%M"), wifi, battery)


def go_home():
    env = dict(os.environ)
    env.setdefault("XDG_RUNTIME_DIR", "/run/nuxel-wayland")
    env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    try:
        subprocess.Popen(["/usr/lib/nuxel/nuxel-foreign-toplevel", "home"],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def log_state(**kw):
    kw["at"] = time.time()
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(kw, f)
    except OSError:
        pass

def normalize(text):
    t = (text or "").strip()
    if not t:
        return None
    if t == "about:blank":
        return t
    if "://" in t:
        return t
    if "." in t and " " not in t:
        return "https://" + t
    import urllib.parse
    return "https://duckduckgo.com/?q=" + urllib.parse.quote(t)

def setup_control(view):
    """One control FIFO per browser instance; last launch wins.  Commands:
    back | forward | reload | status."""
    try:
        os.unlink(CTRL_FIFO)
    except OSError:
        pass
    try:
        os.mkfifo(CTRL_FIFO, 0o600)
    except OSError:
        pass
    rfd = os.open(CTRL_FIFO, os.O_RDONLY | os.O_NONBLOCK)
    # Keep a write end open so the read end never sees EOF when no shell writer.
    try:
        _wfd = os.open(CTRL_FIFO, os.O_WRONLY | os.O_NONBLOCK)
    except OSError:
        _wfd = None

    def publish_nav():
        log_state(status="finished" if view.get_uri() else "blank",
                  uri=view.get_uri() or "",
                  title=view.get_title() or "",
                  can_go_back=view.can_go_back(),
                  can_go_forward=view.can_go_forward())

    def on_cmd(source, condition):
        del source, condition
        try:
            data = os.read(rfd, 4096)
        except OSError:
            return True
        if not data:
            return True
        for line in data.decode("utf-8", "replace").splitlines():
            cmd = line.strip()
            if cmd == "back":
                if view.can_go_back():
                    view.go_back()
                    log_state(status="back-handled", uri=view.get_uri() or "",
                              can_go_back=view.can_go_back(),
                              can_go_forward=view.can_go_forward())
                else:
                    log_state(status="back-at-root", uri=view.get_uri() or "",
                              can_go_back=False,
                              can_go_forward=view.can_go_forward())
            elif cmd == "forward":
                if view.can_go_forward():
                    view.go_forward()
                    log_state(status="forward-handled", uri=view.get_uri() or "",
                              can_go_back=view.can_go_back(),
                              can_go_forward=view.can_go_forward())
            elif cmd == "reload":
                view.reload()
            elif cmd.startswith("navigate "):
                url = normalize(cmd[len("navigate "):].strip())
                if url:
                    view.load_uri(url)
                    log_state(status="navigating", uri=url,
                              can_go_back=view.can_go_back(),
                              can_go_forward=view.can_go_forward())
            elif cmd == "status":
                publish_nav()
        return True

    GLib.io_add_watch(GLib.IOChannel.unix_new(rfd),
                      GLib.PRIORITY_DEFAULT,
                      GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR,
                      on_cmd)

def main():
    start_url = normalize(os.environ.get("NUXEL_BROWSER_URL", "https://www.google.nl"))
    win = Gtk.Window(title="Nuxel Browser")
    win.set_default_size(360, 760)
    # A65-15: drop the redundant per-app GTK titlebar. The browser's own top
    # toolbar is the only chrome; global Back/Home/Tabs remain system-owned.
    win.set_decorated(False)
    win.connect("destroy", Gtk.main_quit)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    win.add(vbox)

    # Native top bar.  A native xdg_toplevel cannot paint the DOM shell's
    # status bar, so the same information and an unconditional exit are kept
    # here.  The system nav dock remains the authoritative Back/Home/Recents.
    system_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    system_bar.set_margin_top(2); system_bar.set_margin_start(6); system_bar.set_margin_end(6)
    sys_title = Gtk.Label(label="Nuxel Browser")
    sys_title.set_xalign(0.0)
    sys_status = Gtk.Label(label=status_text())
    sys_status.set_xalign(0.0)
    sys_status.set_hexpand(True)
    home_btn = Gtk.Button(label="⌂")
    home_btn.set_relief(Gtk.ReliefStyle.NONE)
    close_btn = Gtk.Button(label="✕")
    close_btn.set_relief(Gtk.ReliefStyle.NONE)
    for w in (sys_title, sys_status, home_btn, close_btn):
        system_bar.pack_start(w, False, False, 0)
    vbox.pack_start(system_bar, False, False, 0)
    home_btn.connect("clicked", lambda *a: (go_home(), win.hide()))
    close_btn.connect("clicked", lambda *a: win.destroy())

    def refresh_status(*_a):
        sys_status.set_text(status_text())
        return True
    GLib.timeout_add_seconds(15, refresh_status)

    chrome = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    chrome.set_margin_top(4); chrome.set_margin_start(4); chrome.set_margin_end(4)

    back = Gtk.Button(label="‹"); back.set_tooltip_text("Back")
    fwd = Gtk.Button(label="›"); fwd.set_tooltip_text("Forward")
    reload_ = Gtk.Button(label="⟳"); reload_.set_tooltip_text("Reload")

    entry = Gtk.Entry()
    entry.set_placeholder_text("Search or address")
    entry.set_hexpand(True)
    entry.set_width_chars(8)

    go = Gtk.Button(label="Go")

    for b in (back, fwd, reload_, go):
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_focus_on_click(False)
        try:
            b.set_margin_top(0); b.set_margin_bottom(0)
        except Exception:
            pass
    for w in (back, fwd, reload_, entry, go):
        chrome.pack_start(w, False, False, 0)
    vbox.pack_start(chrome, False, False, 0)

    view = WebKit2.WebView()
    view.set_hexpand(True); view.set_vexpand(True)
    vbox.pack_start(view, True, True, 0)

    def on_go(*a):
        u = normalize(entry.get_text())
        if u:
            view.load_uri(u)

    back.connect("clicked", lambda *a: view.go_back())
    fwd.connect("clicked", lambda *a: view.go_forward())
    reload_.connect("clicked", lambda *a: view.reload())
    go.connect("clicked", on_go)
    entry.connect("activate", on_go)

    def on_uri(v, pspec):
        uri = view.get_uri() or ""
        entry.set_text(uri)
        log_state(status="navigating", uri=uri,
                  can_go_back=view.can_go_back(),
                  can_go_forward=view.can_go_forward())

    def on_load_changed(v, event):
        if event == WebKit2.LoadEvent.STARTED:
            log_state(status="loading", uri=view.get_uri() or "",
                      can_go_back=view.can_go_back(),
                      can_go_forward=view.can_go_forward())
        elif event == WebKit2.LoadEvent.COMMITTED:
            log_state(status="committed", uri=view.get_uri() or "",
                      can_go_back=view.can_go_back(),
                      can_go_forward=view.can_go_forward())
        elif event == WebKit2.LoadEvent.FINISHED:
            log_state(status="finished", uri=view.get_uri() or "",
                      title=view.get_title() or "",
                      can_go_back=view.can_go_back(),
                      can_go_forward=view.can_go_forward())

    def on_load_failed(v, event, uri, err):
        log_state(status="failed", uri=uri or "", error=str(err) if err else "unknown",
                  can_go_back=view.can_go_back(),
                  can_go_forward=view.can_go_forward())
        return False

    def on_enter_fullscreen(*_a):
        # Fullscreen is not allowed to become a trap: keep the system bars and
        # an explicit exit path.  Deny the request and restore the window.
        try:
            win.unfullscreen()
        except Exception:
            pass
        log_state(status="fullscreen-denied", uri=view.get_uri() or "")
        return True

    view.connect("notify::uri", on_uri)
    view.connect("load-changed", on_load_changed)
    view.connect("load-failed", on_load_failed)
    view.connect("enter-fullscreen", on_enter_fullscreen)

    log_state(status="starting", url=start_url,
              can_go_back=view.can_go_back(), can_go_forward=view.can_go_forward())
    setup_control(view)
    view.load_uri(start_url)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
