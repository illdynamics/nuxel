from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_third_row_exists_below_two_existing_rows_and_starts_hidden():
    html = (ROOT / 'pwa/nuxel-home/index.html').read_text()
    first = html.index('id="qs-wifi"')
    second = html.index('id="qs-dnd"')
    third = html.index('id="qs-privacy-row"')
    assert first < second < third
    row = html[third:html.index('>', third) + 1]
    assert 'hidden' in row
    for tile in ('qs-nfc', 'qs-fingerprint', 'qs-camera', 'qs-microphone'):
        assert f'id="{tile}"' in html


def test_row_is_revealed_only_in_expanded_state():
    css = (ROOT / 'pwa/nuxel-home/css/status-bar.css').read_text()
    js = (ROOT / 'pwa/nuxel-home/js/qs.js').read_text()
    assert '#quick-settings:not(.expanded) #qs-privacy-row { display: none !important; }' in css
    assert "privacy.hidden = !on" in js


def test_tiles_use_real_providers_and_acknowledge_before_update():
    js = (ROOT / 'pwa/nuxel-home/js/qs.js').read_text()
    for verb in ("'nfc', 'set-enabled'", "'security', 'set-biometric-unlock'",
                 "'privacy', 'camera-set'", "'privacy', 'microphone-set'"):
        assert verb in js, verb
    assert 'await this._syncPrivacy();' in js
    assert "provider did not confirm" in js


def test_privacy_provider_wired_in_bridge():
    api = (ROOT / 'services/nuxel-bridge/src/api.py').read_text()
    assert "'privacy_provider'" in api
    assert "'privacy': privacy_provider" in api
    bridge = (ROOT / 'services/nuxel-bridge/src/bridge.py').read_text()
    assert 'CAMERA_PRIVACY_BLOCKED' in bridge
    assert 'privacy_provider' in bridge
