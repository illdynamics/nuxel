#!/usr/bin/env python3
"""PWNAGE-103000 page-side probe (read-only, device).

Loads the RUNNING Home document in an offscreen WebKit view and prints the
loaded Edge Lighting engine registry + status as one JSON line.  It does not
open the panel, change settings, create notifications or touch any LED.
"""
import json
import sys
import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2  # noqa: E402

URL = "http://127.0.0.1:8000/pwa/nuxel-home/index.html"
win = Gtk.OffscreenWindow()
view = WebKit2.WebView.new_with_context(WebKit2.WebContext.get_default())
view.set_size_request(360, 760)
win.add(view)
win.show_all()
view.load_uri(URL)
deadline = time.time() + 25
while time.time() < deadline:
    Gtk.main_iteration_do(False)
    time.sleep(0.02)

box = {}


def done(_view, res, _data=None):
    try:
        box["v"] = _view.evaluate_javascript_finish(res).to_string()
    except Exception as exc:  # noqa: BLE001
        box["e"] = str(exc)


view.evaluate_javascript(
    "JSON.stringify(window.NuxelEdgeLighting ? {loaded:true,effects:NuxelEdgeLighting.EFFECTS,"
    "default:NuxelEdgeLighting.DEFAULTS.effect,status:NuxelEdgeLighting.status()} : {loaded:false})",
    -1, None, None, None, done, None)
deadline = time.time() + 10
while "v" not in box and "e" not in box and time.time() < deadline:
    Gtk.main_iteration_do(False)
    time.sleep(0.01)
print(box.get("v") or json.dumps({"state": "PROBE_TIMEOUT", "error": box.get("e")}))
sys.exit(0 if "v" in box else 1)
