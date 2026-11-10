#!/usr/bin/env python3
"""Offline gate for physical USB HID mouse/keyboard support and its Settings UI.

Checks the whole chain, without a phone:
  * the libinput shim selects pointer/keyboard nodes by capability and keeps the
    DIRECT touch calibration path unchanged (fixture test owns the behaviour);
  * /etc/nuxel/input/input.json defaults match the Settings model;
  * nuxel-input-apply.sh validates the document, writes GSettings and its state
    (its own stub-gsettings selftest is executed);
  * Settings exposes the new controls and script, and the launcher host can read
    the document + both consumer state files.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
A33 = HERE.parent
ROOT = A33.parents[2]
FIX = HERE / "fixtures" / "usb-hid"

failures = []


def ck(cond, what, extra=""):
    if cond:
        print("PASS %s" % what)
    else:
        print("FAIL %s%s" % (what, (" :: " + extra) if extra else ""))
        failures.append(what)


def text(rel):
    try:
        return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


doc = json.loads(text("configs/nuxel/input/input.json"))
model = text("pwa/nuxel-apps/settings/settings-model.js")
html = text("pwa/nuxel-apps/settings/index.html")
js = text("pwa/nuxel-apps/settings/physical-input-settings.js")
applier = text("tools/s10plus/a33/nuxel-input-apply.sh")
shim = text("tools/s10plus/a33/nuxel-libinput-path.c")
pwa33 = text("tools/s10plus/a33/nuxel-pwa-host.c")
pwa45 = text("tools/s10plus/a45/nuxel-pwa-host.c")

print("== document and Settings model ==")
ck(doc.get("schema_version") == 1, "input document has schema_version 1")
ck("nuxel-libinput-path.so" in doc.get("consumer", ""), "document names the libinput shim consumer")
ck("nuxel-input-apply.sh" in doc.get("consumer", ""), "document names the GSettings applier consumer")
for key, value in (
    ("mouse.speed", 0.4), ("mouse.accel_profile", "flat"),
    ("mouse.natural_scroll", False), ("mouse.left_handed", False),
    ("mouse.middle_emulation", False), ("touchpad.speed", 0.0),
    ("touchpad.accel_profile", "default"), ("touchpad.natural_scroll", True),
    ("touchpad.tap_to_click", True), ("touchpad.two_finger_scroll", True),
    ("touchpad.disable_while_typing", True), ("touchpad.left_handed", False),
):
    ck(doc.get(key) == value, "input.json default %s = %r" % (key, value))
    ck("'%s'" % key in model, "Settings model declares %s" % key)
ck("'input': { path: '/etc/nuxel/input/input.json'" in model, "Settings model names the input document and consumer")
ck("pointer: [" in model, "Settings model has the pointer group")

print("== shim selection stays capability-based ==")
for needle in ("CAND_POINTER", "CAND_KEYBOARD", "CAND_TOUCH", "INPUT_CFG_LOADED",
               "INPUT_APPLY_POINTER", "INPUT_STATE", "by-path"):
    ck(needle in shim, "shim carries %s" % needle)
ck("ID_INPUT_TOUCHSCREEN=1" in shim and "if (c->kind & CAND_TOUCH)" in shim,
   "the touchscreen udev tag is gated by kind (no keyboard tagged as touch)")
ck("key_letters >= 10" in shim, "a keyboard needs the standard letter block")
ck("c->rel_x && c->rel_y" in shim or "(c->rel_x && c->rel_y)" in shim.lower(),
   "a relative pointer needs REL_X/Y")
ck("calibrate_device(name, dev, c.kind" in shim or "calibrate_device(sel[i].name, dev, sel[i].kind" in shim,
   "calibration is passed the device kind")
for needle in ("HOTPLUG_WAKE_READY", "wl_display_get_event_loop", "wake_event_cb",
               "HOTPLUG_REPLACE", "node_stat_ino", "RETRY_ATTEMPTS", "c->ino"):
    ck(needle in shim, "shim carries %s" % needle)
ck("shim_libinput_remove(dev)" not in shim and
   "libinput_path_remove_device((struct libinput_device *)" not in shim,
   "the shim never calls libinput_path_remove_device from the dispatch path")
ck("WL_EVENT_READABLE" in shim or "NUXEL_WL_EVENT_READABLE" in shim,
   "the compositor loop is woken through a Wayland event source")

print("== applier ==")
rc = subprocess.run([str(ROOT / "tools/s10plus/a33/nuxel-input-apply.sh"), "selftest"],
                    capture_output=True, text=True, timeout=60)
ck(rc.returncode == 0 and "SELFTEST_OK" in rc.stdout, "nuxel-input-apply selftest passes",
   (rc.stdout + rc.stderr)[:300])
for key in ("org.gnome.desktop.peripherals.mouse", "org.gnome.desktop.peripherals.touchpad",
            "tap-to-click", "two-finger-scrolling-enabled", "disable-while-typing",
            "input-gsettings.state"):
    ck(key in applier, "applier writes %s" % key)

print("== Settings panel and launcher host ==")
for needle in ('data-tab="mouse"', 'id="tab-mouse"', 'id="pi-mouse-speed"',
               'id="pi-touchpad-tap"', 'id="pi-keyboard-layout"',
               'id="pi-save-pointer"', 'id="pi-save-keyboard"',
               'physical-input-settings.js'):
    ck(needle in html, "Settings HTML has %s" % needle)
for needle in ("config.get', { name: 'input'", "config.get', { name: 'keyboard'",
               "config.set', { name: 'input'", "config.set', { name: 'keyboard'",
               "status.read', { name: 'input-state'", "input-gsettings-state"):
    ck(needle in js, "physical-input-settings.js has %s" % needle)
for rel, src in (("a33", pwa33), ("a45", pwa45)):
    ck('{ "input",               "/etc/nuxel/input/input.json",                  1 }' in src,
       "%s launcher host can read/write the input document" % rel)
    ck('{ "input-state",         "/run/nuxel-input.state",                       0 }' in src,
       "%s launcher host exposes input-state" % rel)
    ck('{ "input-gsettings-state", "/run/nuxel-input-gsettings.state",          0 }' in src,
       "%s launcher host exposes input-gsettings-state" % rel)

print("== units ==")
svc = text("configs/nuxel/input/nuxel-input-apply.service")
path = text("configs/nuxel/input/nuxel-input-apply.path")
ck("/usr/libexec/nuxel/nuxel-input-apply apply" in svc, "service runs the real applier")
ck("PathChanged=/etc/nuxel/input/input.json" in path, "path unit watches the real document")

print("== usb-hid fixture ==")
ck((FIX / "sys/class/input/event5/device/capabilities/rel").is_file(), "fixture has a relative mouse node")
ck((FIX / "sys/class/input/event6/device/capabilities/key").is_file(), "fixture has a keyboard node")

print("== %d failing check(s) ==" % len(failures))
sys.exit(1 if failures else 0)
