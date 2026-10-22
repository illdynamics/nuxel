#!/usr/bin/env python3
"""nuxel-browser-native — a genuine, top-level WebKitGTK browser for Nuxel.

Uses GTK3 + WebKit2GTK 4.1, the same stack the working nuxel-pwa-host launcher
uses on this device (GTK3/WebKit2-4.1 typelibs verified present; the GTK4
WebKit-6.0 web process does not spawn under this vendor 4.14 kernel).

Real WebKitWebView top-level navigation (NOT an iframe); TLS errors fail closed.
"""
import os
import sys
import json
import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2, GLib

STATE_PATH = "/run/nuxel-browser.state"

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

def main():
    start_url = normalize(os.environ.get("NUXEL_BROWSER_URL", "https://www.google.nl"))
    win = Gtk.Window(title="Nuxel Browser")
    win.set_default_size(360, 760)
    win.connect("destroy", Gtk.main_quit)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    win.add(vbox)

    chrome = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    chrome.set_margin_top(4); chrome.set_margin_start(4); chrome.set_margin_end(4)

    back = Gtk.Button(label="‹"); back.set_tooltip_text("Back")
    fwd = Gtk.Button(label="›"); fwd.set_tooltip_text("Forward")
    reload_ = Gtk.Button(label="⟳"); reload_.set_tooltip_text("Reload")

    entry = Gtk.Entry()
    entry.set_placeholder_text("https://www.google.nl")
    entry.set_hexpand(True)

    go = Gtk.Button(label="Go")

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
        log_state(status="navigating", uri=uri)

    def on_load_changed(v, event):
        if event == WebKit2.LoadEvent.STARTED:
            log_state(status="loading", uri=view.get_uri() or "")
        elif event == WebKit2.LoadEvent.COMMITTED:
            log_state(status="committed", uri=view.get_uri() or "")
        elif event == WebKit2.LoadEvent.FINISHED:
            log_state(status="finished", uri=view.get_uri() or "", title=view.get_title() or "")

    def on_load_failed(v, event, uri, err):
        log_state(status="failed", uri=uri or "", error=str(err) if err else "unknown")
        return False

    view.connect("notify::uri", on_uri)
    view.connect("load-changed", on_load_changed)
    view.connect("load-failed", on_load_failed)

    log_state(status="starting", url=start_url)
    view.load_uri(start_url)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
