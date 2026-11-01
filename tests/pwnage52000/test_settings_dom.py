import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / 'pwa/nuxel-apps/settings'


def ids(path):
    return re.findall(r'\bid="([^"]+)"', path.read_text())


def test_settings_ids_are_unique():
    seen = {}
    for name in ids(SETTINGS / 'index.html'):
        assert name not in seen, f'duplicate Settings id: {name}'
        seen[name] = True


def test_required_unique_display_ids():
    doc = (SETTINGS / 'index.html').read_text()
    for name in ('screen-state', 'graphics-acceleration-state',
                 'graphics-acceleration-detail', 'external-display-state',
                 'external-display-detail', 'dev-state'):
        assert doc.count(f'id="{name}"') == 1, name
    assert 'id="display-state"' not in doc


def test_no_duplicate_ids_in_installed_pwas():
    files = list((ROOT / 'pwa/nuxel-apps').glob('*/index.html'))
    files.append(ROOT / 'pwa/nuxel-home/index.html')
    for path in files:
        doc = path.read_text()
        found = re.findall(r'\bid="([^"]+)"', doc)
        assert len(found) == len(set(found)), f'duplicate id in {path}'


def test_settings_css_width_contract():
    css = (SETTINGS / 'settings.css').read_text()
    assert 'overflow-x: clip' in css
    assert 'grid-template-columns: repeat(10, minmax(0, 1fr))' in css
    assert 'overflow-x: auto' in css  # tab rail only
    assert 'min-width: 0' in css


def test_developer_refresh_cannot_write_screen_or_displays():
    js = (SETTINGS / 'settings.js').read_text()
    body = js[js.index('function refreshDev'):js.index("document.getElementById('refresh-dev')")]
    assert "getElementById('display-state')" not in body
    assert "getElementById('external-display-state')" not in body
    assert "getElementById('graphics-acceleration-state')" not in body
    assert "getElementById('dev-state')" in body
    assert "getElementById('screen-state')" in body
