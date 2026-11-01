from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_css_hides_topbar_and_dom_nav_while_locked():
    css = (ROOT / 'pwa/nuxel-home/css/lockscreen.css').read_text()
    status = (ROOT / 'pwa/nuxel-home/css/status-bar.css').read_text()
    assert 'body.lockscreen-active #status-bar' in css
    assert 'body.lockscreen-active #system-navigation' in css
    assert 'display: none !important' in css
    assert 'body.lockscreen-active .status-bar' in status
    # The old rule that raised the bar above the lockscreen must be gone.
    assert 'body.lockscreen-active .status-bar {\n    display: grid !important;' not in status


def test_lock_hides_chrome_and_native_dock_before_reveal():
    js = (ROOT / 'pwa/nuxel-home/js/app.js').read_text()
    body = js[js.index('    _lock(reason)'):js.index('    _unlock(reason)')]
    assert body.index("classList.add('lockscreen-active')") < body.index("this._setNavDock(false)") < body.index('this.lockscreen.show')
    assert body.index('this._setNavDock(false)') < body.index('this.lockscreen.show')


def test_unlock_restores_native_dock_only_after_home():
    js = (ROOT / 'pwa/nuxel-home/js/app.js').read_text()
    body = js[js.index('    _unlock(reason)'):js.index('    _enterHomeAfterUnlock')]
    assert body.index('ls.hide()') < body.index('_enterHomeAfterUnlock') < body.index('_setNavDock(true)')


def test_navdock_starts_hidden_and_refuses_show_while_locked():
    c = (ROOT / 'tools/s10plus/a45/nuxel-navdock.c').read_text()
    assert 'static int dock_visible = 0;' in c
    assert 'NAV_DOCK_SHOW_REFUSED' in c
    assert 'lock_state_read()' in c
    assert 'dock_resolve_startup();' in c


def test_host_reads_authoritative_security_lock_state():
    host = (ROOT / 'tools/s10plus/a45/nuxel-pwa-host.c').read_text()
    assert '/run/nuxel/security/lock-state.json' in host
    assert '/run/nuxel-lock.state' not in host
