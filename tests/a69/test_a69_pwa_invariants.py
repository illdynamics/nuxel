"""A69 PWA invariant tests — offline assertions over the real launcher sources.

These prove the *single-owner* fixes are actually present in the shipped files,
without requiring the phone. Physical acceptance remains a separate gate.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_nav_host_count_one_dom_owner():
    html = read("pwa/nuxel-home/index.html")
    # Exactly one DOM nav element; the native layer-shell dock is the only
    # other host, and navigation.js hides the DOM copy when the native one is up.
    assert html.count('id="system-navigation"') == 1


def test_native_nav_present_hides_dom_nav():
    css = read("pwa/nuxel-home/css/style.css")
    assert ".native-nav-present #system-navigation { display: none; }" in css


def test_app_foreground_hides_dock_and_drawer():
    css = read("pwa/nuxel-home/css/style.css")
    assert 'body[data-app-state="ACTIVE"] #dock,' in css
    assert 'body[data-app-state="ACTIVE"] #app-grid,' in css
    assert 'body[data-app-state="LAUNCHING"] #app-grid { display: none; }' in css


def test_app_launch_dismisses_drawer():
    js = read("pwa/nuxel-home/js/app.js")
    assert "this._dismissLauncherChrome();" in js
    # Called from the app:launch handler, PWA open and native launch.
    assert js.count("this._dismissLauncherChrome();") >= 3


def test_lockscreen_battery_prefers_host_and_converges_fast():
    js = read("pwa/nuxel-home/js/lockscreen.js")
    assert "statusRead('battery-capacity')" in js
    assert "global.setTimeout(() => this._updateBattery(), 1000);" in js
    assert "global.setTimeout(() => this._updateBattery(), 3000);" in js
    # No fabricated 0% default: null still renders the neutral em dash.
    assert "shown === null ? '—'" in js
