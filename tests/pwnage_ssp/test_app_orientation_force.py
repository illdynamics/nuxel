#!/usr/bin/env python3
"""Per-app orientation: default (initial pose) vs FORCE (locked pose).

Source-level gates for the bridge data model + the Settings UI, plus a real
round-trip of the JSON helpers against a temporary document.
"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  %s" % (detail,)))
    if not cond:
        fails.append(name)


api_path = ROOT / "services/nuxel-bridge/src/api.py"
src = api_path.read_text()
check("force helper exists", "def forced_orientation_for_app(" in src)
check("force stored in its own doc key", 'doc.get("force")' in src)
check("force only for an explicit mode",
      "if force and apps.get(app_id) in APP_ORIENTATION_MODES" in src)
check("orientation-defaults returns force", '"force": dict(doc.get("force", {}) or {})' in src)
check("set-default returns forced_orientation",
      '"forced_orientation": forced.get(app_id)' in src)
check("apply-orientation honours force",
      "mode = forced_orientation_for_app(app_id) or mode" in src)
check("launch path honours force first",
      "mode = forced_orientation_for_app(app_id)\n        if mode is None:" in src)
check("focus-watch re-asserts a forced app",
      "orientation focus-watch FORCE" in src)

ui = (ROOT / "pwa/nuxel-apps/settings/apps-permissions-settings.js").read_text()
check("UI renders a Force checkbox", "forceBox.type = 'checkbox'" in ui)
check("UI sends force with the selection", "force: wantedForce" in ui)
check("UI sends force on the checkbox", "force: forceBox.checked" in ui)
check("Force disabled for inherit", "forceBox.disabled = sel.value === 'inherit'" in ui)
check("UI explains force semantics", "until Force is unchecked" in ui)

# Real round-trip of the pure helper functions against a temp document.
# The host may not have python3-dbus (it is a phone dependency).  Provide a
# minimal stand-in ONLY for this import-time unit test; nothing is executed.
import types
if "dbus" not in sys.modules:
    dbus_stub = types.ModuleType("dbus")
    dbus_stub.__path__ = []  # make it importable as a package for submodules
    dbus_stub.SystemBus = lambda *a, **k: None
    dbus_stub.Interface = lambda *a, **k: None
    dbus_stub.exceptions = types.SimpleNamespace(DBusException=Exception)
    mainloop_stub = types.ModuleType("dbus.mainloop")
    glib_stub = types.ModuleType("dbus.mainloop.glib")
    glib_stub.DBusGMainLoop = lambda *a, **k: None
    mainloop_stub.glib = glib_stub
    sys.modules["dbus"] = dbus_stub
    sys.modules["dbus.mainloop"] = mainloop_stub
    sys.modules["dbus.mainloop.glib"] = glib_stub
spec = importlib.util.spec_from_file_location("br_api", api_path)
mod = importlib.util.module_from_spec(spec)
sys.modules["br_api"] = mod
try:
    spec.loader.exec_module(mod)
except Exception as exc:  # noqa: BLE001
    check("bridge api imports", False, exc)
    print("\n%d failing check(s)" % len(fails))
    sys.exit(1)
check("bridge api imports", True)

with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump({"schema_version": 1, "default": "portrait",
               "apps": {"org.nuxel.Doom": "landscape",
                        "org.mozilla.firefox": "portrait"},
               "force": {"org.nuxel.Doom": "landscape"}}, f)
    doc_path = f.name
old_path = mod.APP_ORIENTATION_DEFAULTS
try:
    mod.APP_ORIENTATION_DEFAULTS = doc_path
    check("unforced app has no force", mod.forced_orientation_for_app("org.mozilla.firefox") is None)
    check("forced app returns its mode",
          mod.forced_orientation_for_app("org.nuxel.Doom") == "landscape")
    check("forced mode matches explicit default",
          mod.forced_orientation_for_app("org.nuxel.Doom") ==
          mod.explicit_orientation_for_app("org.nuxel.Doom"))
finally:
    mod.APP_ORIENTATION_DEFAULTS = old_path
    os.unlink(doc_path)

print("\n%d failing check(s)" % len(fails))
sys.exit(1 if fails else 0)
