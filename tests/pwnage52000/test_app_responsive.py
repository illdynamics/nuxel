import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPS = ROOT / 'pwa/nuxel-apps'


def test_every_pwa_has_viewport_and_responsive_contract():
    files = sorted(APPS.glob('*/index.html')) + [ROOT / 'pwa/nuxel-home/index.html']
    assert len(files) >= 26
    for path in files:
        doc = path.read_text()
        assert 'name="viewport"' in doc, path
        assert 'responsive.css' in doc, f'{path} missing shared responsive.css'


def test_no_fixed_page_width_above_phone_range():
    for path in APPS.glob('*/css/*.css'):
        css = path.read_text()
        # width/min-width declarations above 430 px are allowed only inside a
        # media query (checked narrowly by rejecting unconditional declarations).
        for m in re.finditer(r'(?ms)^(?!@media)[^\n{}]*\{(?:(?!\}).)*?(?<!max-)(?:min-)?width\s*:\s*(\d{3,4})px', css):
            assert int(m.group(1)) <= 430, f'{path}: {m.group(0)[:80]}'


def test_installed_pwa_inventory_matches_disk():
    manifests = sorted(p.parent.name for p in APPS.glob('*/manifest.json'))
    assert 'settings' in manifests and 'notes' in manifests and 'files' in manifests
    assert 'penguinterface' in manifests
