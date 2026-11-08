#!/usr/bin/env python3
"""nuxel-browser-native — the canonical, user-facing Nuxel browser.

GTK3 + WebKit2GTK 4.1 top-level WebKitWebView (NOT an iframe).  The launcher
registry points org.nuxel.Browser at this program; the legacy PWA page viewer
under pwa/nuxel-apps/browser is not a launcher entry.

PWNAGE-96000 adds:
  * a top-right vertical three-dot (U+22EE) settings popover;
  * persistent Mobile-site / Desktop-site modes stored in the browser profile;
  * Desktop mode changes the REAL WebKit User-Agent of this WebView only and
    reloads the page (no global UA, no DOM/CSS spoof).

TLS errors fail closed (WebKitGTK default).  No sandbox/security weakening.
The system Back contract remains /run/nuxel-browser.state + .cmd; Back closes
an open menu first, then navigates browser history, then reports at_root.
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
SETTINGS_PATH = os.environ.get(
    "NUXEL_BROWSER_SETTINGS", "/var/lib/nuxel/browser/settings.json")
SETTINGS_VERSION = 1
VERSION = "0.8.2-beta"

UA_MOBILE = (
    "Mozilla/5.0 (Linux; Android 14; SM-G975F) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 "
    "NuxelBrowser/" + VERSION)
UA_DESKTOP = (
    "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15 "
    "NuxelBrowser/" + VERSION)

_site_mode = "mobile"
_menu_open = False


def normalize_mode(value):
    value = str(value or "").strip().lower()
    if value in ("desktop", "desktop-site", "desktop_site"):
        return "desktop"
    return "mobile"


def user_agent_for(mode):
    return UA_DESKTOP if normalize_mode(mode) == "desktop" else UA_MOBILE


def load_settings():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if isinstance(doc, dict):
            return {"schema_version": SETTINGS_VERSION,
                    "site_mode": normalize_mode(doc.get("site_mode"))}
    except (OSError, ValueError):
        pass
    return {"schema_version": SETTINGS_VERSION, "site_mode": "mobile"}


def save_settings(mode):
    doc = {"schema_version": SETTINGS_VERSION, "site_mode": normalize_mode(mode)}
    directory = os.path.dirname(SETTINGS_PATH)
    tmp = SETTINGS_PATH + ".%d.tmp" % os.getpid()
    try:
        os.makedirs(directory, mode=0o750, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, sort_keys=True)
            fh.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, SETTINGS_PATH)
        return True
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        sys.stderr.write("browser settings save failed: %s\n" % exc)
        return False


def log_state(**kw):
    kw["at"] = time.time()
    kw.setdefault("site_mode", _site_mode)
    kw.setdefault("ua_family", "desktop" if _site_mode == "desktop" else "mobile")
    kw.setdefault("menu_open", bool(_menu_open))
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


def setup_control(view, handlers):
    """One control FIFO per browser instance; last launch wins.  Commands:
    back | forward | reload | navigate <url> | mode mobile|desktop |
    menu | menu-close | status.  The schema is backwards compatible."""
    try:
        os.unlink(CTRL_FIFO)
    except OSError:
        pass
    try:
        os.mkfifo(CTRL_FIFO, 0o600)
    except OSError:
        pass
    rfd = os.open(CTRL_FIFO, os.O_RDONLY | os.O_NONBLOCK)
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
                if handlers["menu_is_open"]():
                    handlers["menu_close"]()
                    log_state(status="menu-closed-back",
                              uri=view.get_uri() or "",
                              can_go_back=view.can_go_back(),
                              can_go_forward=view.can_go_forward())
                elif view.can_go_back():
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
            elif cmd.startswith("mode "):
                handlers["set_mode"](cmd[len("mode "):].strip(), True)
            elif cmd == "menu":
                handlers["menu_open"]()
            elif cmd == "menu-close":
                handlers["menu_close"]()
            elif cmd == "status":
                publish_nav()
        return True

    GLib.io_add_watch(GLib.IOChannel.unix_new(rfd),
                      GLib.PRIORITY_DEFAULT,
                      GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR,
                      on_cmd)


BROWSER_CSS = b"""
.browser-top { background: #101820; }
.browser-top button { min-height: 38px; min-width: 38px; padding: 0 6px; }
.browser-menu { background: #101820; color: #eaf2f8; padding: 10px; }
.browser-menu label { color: #eaf2f8; }
.browser-menu .menu-title { font-size: 13px; font-weight: 700; color: #8fa2b3; }
.browser-menu .menu-note { font-size: 11px; color: #8fa2b3; }
.browser-menu radiobutton { min-height: 46px; }
.browser-menu button.menu-row { min-height: 46px; }
"""


def main():
    global _site_mode, _menu_open
    settings = load_settings()
    _site_mode = settings["site_mode"]
    start_url = normalize(os.environ.get("NUXEL_BROWSER_URL", "https://www.google.nl"))

    win = Gtk.Window(title="Nuxel Browser")
    win.set_default_size(360, 760)
    win.maximize()
    win.set_decorated(False)
    win.connect("destroy", Gtk.main_quit)

    provider = Gtk.CssProvider()
    provider.load_from_data(BROWSER_CSS)
    screen = win.get_screen()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    vbox.set_margin_top(14)
    vbox.set_margin_bottom(10)
    vbox.set_margin_start(3)
    vbox.set_margin_end(3)
    vbox.get_style_context().add_class("browser-top")
    win.add(vbox)

    chrome = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
    back = Gtk.Button(label="\u2039"); back.set_tooltip_text("Back")
    fwd = Gtk.Button(label="\u203a"); fwd.set_tooltip_text("Forward")
    reload_ = Gtk.Button(label="\u27f3"); reload_.set_tooltip_text("Reload")
    entry = Gtk.Entry()
    entry.set_placeholder_text("Search or address")
    entry.set_hexpand(True)
    entry.set_width_chars(6)
    go = Gtk.Button(label="\u2192"); go.set_tooltip_text("Go")
    menu_btn = Gtk.MenuButton()
    menu_btn.set_label("\u22ee")
    menu_btn.set_tooltip_text("Browser settings")
    menu_btn.set_relief(Gtk.ReliefStyle.NONE)
    try:
        menu_btn.get_accessible().set_name("Browser settings")
    except Exception:
        pass
    for b in (back, fwd, reload_, go, menu_btn):
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_focus_on_click(False)
        b.set_size_request(38, 38)
    for w in (back, fwd, reload_, entry, go, menu_btn):
        chrome.pack_start(w, False, False, 0)
    entry.set_hexpand(True)
    vbox.pack_start(chrome, False, False, 0)

    wsettings = WebKit2.Settings()
    wsettings.set_user_agent(user_agent_for(_site_mode))
    view = WebKit2.WebView.new_with_settings(wsettings)
    view.set_hexpand(True)
    view.set_vexpand(True)
    vbox.pack_start(view, True, True, 0)

    # ---- settings popover (top-right vertical three-dot menu) ----------
    popover = Gtk.Popover.new(menu_btn)
    popover.set_modal(True)
    try:
        popover.set_position(Gtk.PositionType.BOTTOM)
    except Exception:
        pass
    menu_btn.set_popover(popover)
    menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    menu_box.set_margin_top(6)
    menu_box.set_margin_bottom(6)
    menu_box.set_margin_start(6)
    menu_box.set_margin_end(6)
    menu_box.get_style_context().add_class("browser-menu")
    menu_box.set_size_request(264, -1)

    title = Gtk.Label(label="Site mode")
    title.set_xalign(0.0)
    title.get_style_context().add_class("menu-title")
    menu_box.pack_start(title, False, False, 0)

    mobile_rb = Gtk.RadioButton.new_with_label_from_widget(None, "Mobile site")
    desktop_rb = Gtk.RadioButton.new_with_label_from_widget(mobile_rb, "Desktop site")
    for rb in (mobile_rb, desktop_rb):
        rb.set_halign(Gtk.Align.START)
        rb.set_margin_start(6)
        menu_box.pack_start(rb, False, False, 0)
    note = Gtk.Label(label="Desktop mode changes the real WebKit User-Agent and "
                            "reloads the current page. Pinch to zoom.")
    note.set_xalign(0.0)
    note.set_line_wrap(True)
    note.set_max_width_chars(34)
    note.get_style_context().add_class("menu-note")
    menu_box.pack_start(note, False, False, 0)
    menu_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

    reload_row = Gtk.Button(label="Reload page")
    reload_row.get_style_context().add_class("menu-row")
    reload_row.connect("clicked", lambda *_: (popover.popdown(), view.reload()))
    menu_box.pack_start(reload_row, False, False, 0)
    close_row = Gtk.Button(label="Close menu")
    close_row.get_style_context().add_class("menu-row")
    close_row.connect("clicked", lambda *_: popover.popdown())
    menu_box.pack_start(close_row, False, False, 0)
    popover.add(menu_box)

    mode_ui_guard = {"busy": False}

    def sync_mode_ui():
        mode_ui_guard["busy"] = True
        try:
            mobile_rb.set_active(_site_mode != "desktop")
            desktop_rb.set_active(_site_mode == "desktop")
        finally:
            mode_ui_guard["busy"] = False

    def set_mode(mode, reload_page=True):
        global _site_mode
        mode = normalize_mode(mode)
        _site_mode = mode
        wsettings.set_user_agent(user_agent_for(mode))
        try:
            # Desktop pages are laid out for a wider viewport.  Fit-to-width is
            # a presentation aid; the User-Agent switch above is the real mode.
            view.set_zoom_level(-1.35 if mode == "desktop" else 0.0)
        except Exception:
            pass
        save_settings(mode)
        sync_mode_ui()
        win.set_title("Nuxel Browser \u2014 Desktop site" if mode == "desktop"
                      else "Nuxel Browser")
        log_state(status="mode-" + mode, uri=view.get_uri() or "",
                  can_go_back=view.can_go_back(),
                  can_go_forward=view.can_go_forward())
        if reload_page and view.get_uri():
            log_state(status="reloading-mode", uri=view.get_uri() or "",
                      can_go_back=view.can_go_back(),
                      can_go_forward=view.can_go_forward())
            view.reload()

    def on_mode_toggled(_rb):
        if mode_ui_guard["busy"]:
            return
        set_mode("desktop" if desktop_rb.get_active() else "mobile", True)

    mobile_rb.connect("toggled", on_mode_toggled)
    desktop_rb.connect("toggled", on_mode_toggled)
    sync_mode_ui()

    def menu_is_open():
        return bool(popover.get_visible())

    def menu_open():
        if not popover.get_visible():
            log_state(status="menu-requested", uri=view.get_uri() or "",
                      can_go_back=view.can_go_back(),
                      can_go_forward=view.can_go_forward())
            # Let GtkMenuButton own the popup placement/toggle; calling
            # GtkPopover.popup() directly can be ignored while the button owns it.
            menu_btn.emit("clicked")

    def menu_close():
        if popover.get_visible():
            popover.popdown()

    def on_popover_show(*_a):
        global _menu_open
        _menu_open = True
        log_state(status="menu-open", uri=view.get_uri() or "",
                  can_go_back=view.can_go_back(),
                  can_go_forward=view.can_go_forward())

    def on_popover_hide(*_a):
        global _menu_open
        _menu_open = False
        log_state(status="menu-closed", uri=view.get_uri() or "",
                  can_go_back=view.can_go_back(),
                  can_go_forward=view.can_go_forward())

    popover.connect("show", on_popover_show)
    popover.connect("hide", on_popover_hide)

    def on_go(*_a):
        u = normalize(entry.get_text())
        if u:
            view.load_uri(u)

    def on_back(*_a):
        if menu_is_open():
            menu_close()
        else:
            view.go_back()

    back.connect("clicked", on_back)
    fwd.connect("clicked", lambda *_: view.go_forward())
    reload_.connect("clicked", lambda *_: view.reload())
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
            if _site_mode == "desktop":
                try:
                    view.set_zoom_level(-1.35)
                except Exception:
                    pass
            log_state(status="committed", uri=view.get_uri() or "",
                      can_go_back=view.can_go_back(),
                      can_go_forward=view.can_go_forward())
        elif event == WebKit2.LoadEvent.FINISHED:
            log_state(status="finished", uri=view.get_uri() or "",
                      title=view.get_title() or "",
                      can_go_back=view.can_go_back(),
                      can_go_forward=view.can_go_forward())

    def on_load_failed(v, event, uri, err):
        log_state(status="failed", uri=uri or "",
                  error=str(err) if err else "unknown",
                  can_go_back=view.can_go_back(),
                  can_go_forward=view.can_go_forward())
        return False

    def on_enter_fullscreen(*_a):
        # Fullscreen is not allowed to become a trap: keep an explicit exit.
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

    handlers = {
        "menu_is_open": menu_is_open,
        "menu_open": menu_open,
        "menu_close": menu_close,
        "set_mode": set_mode,
    }
    setup_control(view, handlers)

    log_state(status="starting", url=start_url,
              can_go_back=view.can_go_back(), can_go_forward=view.can_go_forward(),
              settings_path=SETTINGS_PATH)
    view.load_uri(start_url)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
