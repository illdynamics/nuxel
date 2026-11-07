import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / 'pwa/nuxel-apps/settings'


def test_graphics_block_precedes_external_connector_block():
    html = (SETTINGS / 'index.html').read_text()
    g = html.index('id="graphics-acceleration-card"')
    e = html.index('id="external-display-state"')
    assert g < e


def test_graphics_status_and_test_are_separate_namespaces():
    api = (ROOT / 'services/nuxel-bridge/src/api.py').read_text()
    assert "namespace == 'graphics' and verb in ('status', 'get')" in api
    assert "namespace == 'graphics' and verb == 'test'" in api
    assert '_graphics_status' in api
    assert 'nuxel.graphics-status/1' in api


def test_graphics_ui_is_bounded_and_independent():
    js = (SETTINGS / 'graphics-diagnostics.js').read_text()
    hw = (SETTINGS / 'hardware-settings.js').read_text()
    assert "bounded('graphics', 'status', {}, 3000)" in js
    assert "callBounded('display', 'status', {}, 4000)" in hw
    assert "req !== graphicsReq" in js
    assert "req !== _displayReq" in hw
    assert 'never on refresh' in js


def test_graphics_verdict_keeps_phoc_and_webkit_separate():
    api = (ROOT / 'services/nuxel-bridge/src/api.py').read_text()
    assert '"PARTIAL"' in api
    assert 'phoc_accel and webkit_software' in api
    assert 'WebKitGTK remains software' in api


def test_home_gpu_label_only_adds_acc_when_proved():
    js = (ROOT / 'pwa/nuxel-home/js/system-monitor.js').read_text()
    assert "state === 'ACCELERATED'" in js
    assert "GPU (ACC)" in js
    assert "GPU (PARTIAL)" in js
    html = (ROOT / 'pwa/nuxel-home/index.html').read_text()
    assert '>VRAM<' in html
    assert 'GPU MEM (shared)' not in html


def test_gtk_gl_is_measured_from_the_real_host_warning():
    api = (ROOT / 'services/nuxel-bridge/src/api.py').read_text()
    assert 'GTK failed to initialize GL' in api
    assert 'No GL implementation is available' in api
    assert 'gtk_status = "UNAVAILABLE"' in api
