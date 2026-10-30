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


def test_backgrounded_app_is_fully_removed_from_the_glass():
    """A Back/HOME press must not leave the app frame painted under the dock.

    .pwa-frame declares `display: block !important`, so the `hidden` IDL
    property alone is overridden by the cascade.  The lifecycle must therefore
    have both a JS attribute and a matching !important CSS rule for every
    non-foreground state.
    """
    css = read("pwa/nuxel-home/css/style.css")
    js = read("pwa/nuxel-home/js/app.js")
    for selector in (
        '.pwa-frame[hidden],',
        '.pwa-frame[data-nuxel-backgrounded="true"],',
        'body[data-app-state="BACKGROUND"] .pwa-frame,',
        'body[data-app-state="CLOSED"] .pwa-frame,',
    ):
        assert selector in css
    assert 'display: none !important;' in css
    assert "frame.setAttribute('data-nuxel-backgrounded', 'true');" in js
    assert "surface.frame.removeAttribute('data-nuxel-backgrounded');" in js


def test_home_chrome_hides_while_an_app_owns_or_is_leaving_the_glass():
    css = read("pwa/nuxel-home/css/style.css")
    # BACKGROUND is Home's own state: the app frame is gone and the dock must
    # return.  It is therefore deliberately NOT part of the hide list.
    for state in ("ACTIVE", "LAUNCHING", "CLOSING", "FAILED"):
        assert f"body[data-app-state=\"{state}\"] #dock" in css
