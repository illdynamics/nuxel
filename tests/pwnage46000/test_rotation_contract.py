"""PWNAGE-46000 source/build contract tests (offline)."""
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "auto": ("Auto (FULL)", [0, 90, 180, 270]),
    "auto-portrait": ("Auto (PT)", [0, 180]),
    "auto-landscape": ("Auto (LS)", [90, 270]),
    "portrait": ("Locked (PT)", [0]),
    "landscape": ("Locked (LS)", [90]),
    "reverse-portrait": ("Locked (RPT)", [180]),
    "reverse-landscape": ("Locked (RLS)", [270]),
}


def test_orientation_json_exact_modes_and_labels():
    doc = json.loads((ROOT / "configs/nuxel/orientation/orientation.json").read_text())
    assert doc["mode_order"] == list(EXPECTED)
    for mode, (label, allowed) in EXPECTED.items():
        assert doc["modes"][mode]["label"] == label
        assert doc["modes"][mode]["allowed"] == allowed
    assert doc["compositor"]["trial_seconds"] == 0
    assert doc["compositor"]["commit_verified"] is True
    assert doc["compositor"]["output"] == "auto"
    assert doc["compositor"]["transform_map"] == {"0": "normal", "90": "270", "180": "180", "270": "90"}
    assert doc["compositor"]["screencopy_already_transformed"] is True


def test_policy_labels_and_legacy_aliases():
    src = (ROOT / "services/nuxel-orientation/nuxel_orientation/policy.py").read_text()
    for label in ("Auto (FULL)", "Auto (PT)", "Auto (LS)", "Locked (PT)",
                  "Locked (LS)", "Locked (RPT)", "Locked (RLS)"):
        assert '"%s"' % label in src
    for alias in ("auto_portrait", "auto_landscape", "reverse_portrait",
                  "reverse_landscape"):
        assert alias in src


def test_apply_backend_uses_real_lookup_and_readback():
    src = (ROOT / "services/nuxel-orientation/nuxel_orientation/apply.py").read_text()
    assert "shutil.which(\"wlr-randr\")" in src
    assert '["wlr-randr", "--json"]' in src
    assert "output_status" in src and "after.get(\"transform\") == transform" in src


def test_bridge_set_requests_apply():
    src = (ROOT / "services/nuxel-bridge/src/bridge.py").read_text()
    m = re.search(r"def set_mode\(self, mode\):(.*?)(?:\n\nclass |\Z)", src, re.S)
    assert m and '"--apply"' in m.group(1)


def test_service_is_continuous_not_oneshot():
    src = (ROOT / "services/nuxel-orientation/systemd/nuxel-orientationd.service").read_text()
    assert "Type=simple" in src
    assert "daemon" in src
    assert "Type=oneshot" not in src
    assert "remainafterexit" not in src.lower()


def test_builder_installs_daemon_config_package_and_service():
    src = (ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    assert "services/nuxel-orientation/nuxel-orientationd" in src
    assert "/usr/libexec/nuxel/nuxel_orientation" in src
    assert "/etc/nuxel/orientation/orientation.json" in src
    assert "nuxel-orientationd.service" in src
    assert "../nuxel-orientationd.service" in src
    assert "tools/s10plus/a67/nuxel-wl-fb.c" in src


def test_active_presenter_never_double_rotates_and_is_sole_fb_owner():
    src = (ROOT / "tools/s10plus/a67/nuxel-wl-fb.c").read_text()
    assert 'ORIENT_STATE "/run/nuxel-wl-fb-orientation"' in src
    assert "publish_orientation_proof" in src
    assert "presenter_rotation=0" in src
    assert "double_rotation=0" in src
    assert "blit_rotated(" not in src
    assert src.count("open(\"/dev/fb0\"") == 1
    assert "FBIOPAN_DISPLAY" in src


def test_ui_exact_labels_and_no_advanced_submenu():
    qs = (ROOT / "pwa/nuxel-home/js/qs.js").read_text()
    settings = (ROOT / "pwa/nuxel-apps/settings/settings.js").read_text()
    for label in ("Auto (FULL)", "Auto (PT)", "Auto (LS)", "Locked (PT)",
                  "Locked (LS)", "Locked (RPT)", "Locked (RLS)"):
        assert "'%s'" % label in qs
        assert "'%s'" % label in settings
    assert "Forced Portrait" not in qs and "Forced Landscape" not in qs
    assert "Reverse Portrait (advanced)" not in settings


def test_console_artwork_has_real_transparency_and_sane_size():
    for name in ("serial", "usb", "wlan"):
        path = ROOT / ("assets/nuxel-console-%s.png" % name)
        im = Image.open(path)
        assert im.mode == "RGBA"
        assert max(im.size) <= 256
        lo, hi = im.getchannel("A").getextrema()
        assert lo == 0 and hi == 255


def test_lockscreen_live_console_is_middle_and_lights_for_wlan():
    html = (ROOT / "pwa/nuxel-home/index.html").read_text()
    i_charge = html.index('id="lockscreen-indicator-charging"')
    i_live = html.index('id="lockscreen-indicator-live"')
    i_usb = html.index('id="lockscreen-indicator-usb"')
    assert i_charge < i_live < i_usb
    js = (ROOT / "pwa/nuxel-home/js/lockscreen-indicators.js").read_text()
    assert "this.state.liveConsole || this.state.wlanConsole" in js
    assert "wlan-console" in js


def test_notes_feedback_helper_preserves_notes():
    src = (ROOT / "tools/pwnage46000/rotation-notes.py").read_text()
    assert "PWNAGE-46000 Rotation Test Feedback" in src
    assert "ANSWER: WAITING" in src
    assert "notes.append(note)" in src
    assert "find_note(notes)" in src
    assert "notes = notes.filter" not in src


def test_blue_dom_keyboard_is_removed_and_native_marker_is_packaged():
    kb = (ROOT / "pwa/nuxel-home/js/touch-keyboard.js").read_text()
    css = (ROOT / "pwa/nuxel-home/css/style.css").read_text()
    manifest = json.loads((ROOT / "pwa/nuxel-home/manifest.json").read_text())
    marker = json.loads((ROOT / "pwa/nuxel-home/keyboard-provider.json").read_text())
    assert "get enabled() { return false; }" in kb
    assert "show(target) {" in kb and "_discardFallback();" in kb
    assert "display: none !important;" in css
    assert manifest["orientation"] == "any"
    assert marker["native"] is True and marker["provider"] == "stevia"


def test_every_rotation_capable_pwa_manifest_allows_any_orientation():
    import glob
    manifests = [ROOT / "pwa/nuxel-home/manifest.json"]
    manifests += [Path(p) for p in glob.glob(str(ROOT / "pwa/nuxel-apps/*/manifest.json"))]
    for path in manifests:
        doc = json.loads(path.read_text())
        assert doc.get("orientation", "any") == "any", (path, doc.get("orientation"))
