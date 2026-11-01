#!/usr/bin/env python3
"""Static contracts for the PWNAGE-54000 application fixes."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond: fails.append(name)

browser = (ROOT / "pwa/nuxel-apps/browser/js/browser.js").read_text()
check("browser address bar selects all on tap/focus",
      "addEventListener('pointerdown', selectAddress)" in browser and
      "input.setSelectionRange(0, input.value.length)" in browser)

appjs = (ROOT / "pwa/nuxel-home/js/app.js").read_text()
check("PWA back at root closes gracefully to Home",
      "back:pwa-at-root-close-to-home" in appjs and "this.home();" in appjs)
check("native back at root closes gracefully to Home",
      "back:native-at-root-close-to-home" in appjs)

cal = (ROOT / "pwa/nuxel-apps/calendar/index.html").read_text()
check("calendar time fields request numeric keyboard",
      all(x in cal for x in ('id="event-start"', 'id="event-end"')) and
      cal.count('inputmode="numeric"') >= 3)
clock_html = (ROOT / "pwa/nuxel-apps/clock/index.html").read_text()
clock_js = (ROOT / "pwa/nuxel-apps/clock/js/clock.js").read_text()
check("clock alarm uses inputmode numeric", 'id="alarm-time" type="text" inputmode="numeric"' in clock_html)
check("clock plays the owner alarm asset", "assets/nuxel-alarm.mp3" in clock_js and "playAlarmSound" in clock_js)

files_html = (ROOT / "pwa/nuxel-apps/files/index.html").read_text()
files_js = (ROOT / "pwa/nuxel-apps/files/js/files.js").read_text()
check("files has a text-only copy-contents action",
      'id="copy-text-btn"' in files_html and "copySelectedText" in files_js and
      "isTextEntry" in files_js and "Refusing to copy binary data" in files_js)

clipper = ROOT / "pwa/nuxel-apps/clipper/index.html"
check("Clipper app exists", clipper.is_file())
check("Clipper stores local history", "nuxel.clipper.history.v1" in (ROOT / "pwa/nuxel-apps/clipper/js/clipper.js").read_text())
apps = (ROOT / "pwa/nuxel-home/js/apps.js").read_text()
check("Clipper is registered in Home", "org.nuxel.Clipper" in apps)
check("PenguInterface uses the owner icon asset", "/assets/nuxel-app-penguinterface.png" in apps)
check("PenguInterface asset is present", (ROOT / "assets/nuxel-app-penguinterface.png").is_file())

contacts = (ROOT / "shell/nuxel-shell/nuxel-contacts/main.c").read_text()
check("Contacts has manual add/edit/save", "on_add_contact_clicked" in contacts and "on_save_clicked" in contacts)
check("Contacts has SIM import/sync/save", "on_import_sim_clicked" in contacts and
      "on_sync_sim_clicked" in contacts and "on_save_to_sim_clicked" in contacts)
check("Contacts forces dark mode", "ADW_COLOR_SCHEME_FORCE_DARK" in contacts)
messages = (ROOT / "shell/nuxel-shell/nuxel-messages/main.c").read_text()
check("Messages forces dark mode", "ADW_COLOR_SCHEME_FORCE_DARK" in messages)
check("Messages has SIM import/sync", "on_import_sim_clicked" in messages and "on_sync_sim_clicked" in messages)
dialer = (ROOT / "shell/nuxel-shell/nuxel-dialer/main.c").read_text()
check("Dialer uses call properties, not SMS properties", "MMCallProperties" in dialer and
      "MM_SMS_PROPERTY_NUMBER" not in dialer)
check("Dialer forces dark mode", "ADW_COLOR_SCHEME_FORCE_DARK" in dialer)

api = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
check("Native launch no longer blocks the UI for a surface poll",
      "launch_requested" in api and "_verify_launch" in api)
store = (ROOT / "services/nuxel-bridge/src/pwa_store.py").read_text()
check("File listing uses one stat per entry", "os.scandir" in store and "follow_symlinks=False" in store)
host = (ROOT / "tools/s10plus/a45/nuxel-pwa-host.c").read_text()
check("Launcher diagnostics log is bounded", "STATE_MAX_BYTES" in host)

print("\n%d failing check(s)" % len(fails))
sys.exit(1 if fails else 0)
