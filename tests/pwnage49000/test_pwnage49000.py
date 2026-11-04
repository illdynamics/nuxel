#!/usr/bin/env python3
"""PWNAGE-49000 offline regression checks for system chrome/navigation.

These are source-level guards only.  Physical S10+ proof must be recorded in
docs/beta-finalization/live/evidence/pwnage-49000/.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel):
    return (ROOT / rel).read_text()


def test_radio_icons_use_single_local_mask_artwork():
    css = read("pwa/nuxel-home/css/status-bar.css")
    assert "01-wifi.png" in css and "04-bluetooth.png" in css
    wifi = re.search(r"\.wifi-icon\s*\{(.*?)\}", css, re.S).group(1)
    bt = re.search(r"\.bluetooth-icon\s*\{(.*?)\}", css, re.S).group(1)
    assert "mask" in wifi and "mask" in bt
    assert "content: none" in css
    # The old CSS pseudo-art must not return.
    assert "border-bottom-color: transparent" not in css
    assert "skew(-8deg" not in css


def test_location_never_claims_fix_from_enabled_alone():
    js = read("pwa/nuxel-home/js/status-bar.js")
    assert "locationEnabled && state === 'fixed'" not in js
    assert "data-state=\"fixed\"][data-kind=\"satellite\"]" in read(
        "pwa/nuxel-home/css/status-bar.css")
    assert "this.state.locationEnabled === true" in js
    assert "state !== 'unknown'" in js


def test_dom_top_bar_is_hidden_while_locked():
    # PWNAGE-52000 reverses the PWNAGE-49000 leak: the lockscreen must not
    # show the top bar at all (status-bar.css and lockscreen.css both enforce
    # the lock boundary; the native dock is unmapped separately).
    css = read("pwa/nuxel-home/css/status-bar.css")
    lock = read("pwa/nuxel-home/css/lockscreen.css")
    assert "body.lockscreen-active .status-bar" in css
    assert "display: none !important" in css.split(
        "body.lockscreen-active .status-bar", 1)[1][:200]
    assert "body.lockscreen-active #status-bar" in lock
    assert "body.lockscreen-active #system-navigation" in lock
    js = read("pwa/nuxel-home/js/status-bar.js")
    assert "_statusInactive() { return this._displayOff(); }" in js
    assert "if (this._displayOff() || this._coveredByLock()) return;" in js


def test_native_statusbar_only_over_foreign_foreground():
    c = read("tools/s10plus/a45/nuxel-statusbar.c")
    assert "native_foreground" in c
    assert "app_id=nuxel-pwa-host" in c
    assert "if (shown) bar_show(); else bar_hide();" in c
    assert "STATUSBAR_HIDDEN reason=lock_or_home" in c


def test_navdock_long_back_uses_distinct_one_shot_haptic():
    c = read("tools/s10plus/a45/nuxel-navdock.c")
    assert 'send_haptic(!strcmp(action, "back-long") ? "long" : "navigation")' in c
    assert "#define LONG_HOLD_MS 700" in c
    assert "#define TAP_SLOP_PX  24" in c
    assert "maybe_long_press" in c
    assert "long_fired = 1;" in c
    assert "if (long_fired) { long_fired = 0; return; }" in c
    # Timer must wake poll rather than waiting for release.
    assert "long_press_timeout_ms()" in c


def test_short_back_root_is_noop_home_is_distinct():
    js = read("pwa/nuxel-home/js/app.js")
    assert "back:pwa-at-root" in js
    assert "back:native-at-root-close-to-home" in js
    assert "back:native-no-foreground" in js
    assert "this.appSession.app.type === 'flatpak'" in js


def test_lock_authority_reconciled_before_refusing_launch():
    js = read("pwa/nuxel-home/js/app.js")
    assert "_reconcileLockThenRetry" in js
    assert "sec.status()" in js
    assert "if (st && st.success !== false && st.locked === false)" in js
    assert "launch:blocked-locked-confirmed" in js
    # Never force the local locked flag false without provider agreement.
    assert "locked = false" not in js


def test_transport_penguins_sit_between_primary_row_and_wordmark():
    css = read("pwa/nuxel-home/css/lockscreen.css")
    main = css.split("PWNAGE-34000 console-transport", 1)[1]
    block = re.search(r"\.lockscreen-transports\s*\{(.*?)\}", main, re.S).group(1)
    assert re.search(r"top:\s*258px", block)


def test_cache_version_bumped():
    # Read the live source of truth instead of pinning a historical version.
    # PWNAGE-73000: the tree intentionally moved past v62000-pw62000; the
    # invariant that matters is that sw.js and manifest.json agree.
    import json

    sw = read("pwa/nuxel-home/sw.js")
    manifest_text = read("pwa/nuxel-home/manifest.json")
    cache = json.loads(manifest_text)["nuxel"]["cache_version"]
    assert cache and cache != "v62000-pw62000"
    assert cache in sw
    assert cache in manifest_text
    html = read("pwa/nuxel-home/index.html")
    assert "status-bar.css?v=p52000" in html
    assert "status-bar.js?v=p56000" in html
    assert "app.js?v=p62000" in html


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as exc:
                failures.append((name, str(exc)))
                print("FAIL", name, exc)
    print("PWNAGE-49000 TESTS:", "ALL PASS" if not failures else "FAILURES")
    raise SystemExit(1 if failures else 0)

def test_usb_mtp_sd_is_bind_export_not_raw_block():
    sh = read("services/nuxel-s10/bin/nuxel-usb-mode.sh")
    assert "SD Card" in sh
    assert "mount --bind" in sh and "sd_bind_stop" in sh
    assert "/sys/block/$base/removable" in sh
    assert "mass_storage" not in sh and "f_mass_storage" not in sh
    assert 'write_activation file_transfer true "mtp"' in sh
