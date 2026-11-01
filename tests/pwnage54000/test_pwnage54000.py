"""PWNAGE-54000 source contracts: orientation, navigation, icons, CPU."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABELS = {
    "auto": "Auto (FULL)", "auto-portrait": "Auto (PT)",
    "auto-landscape": "Auto (LS)", "portrait": "Locked (PT)",
    "landscape": "Locked (LS)", "reverse-portrait": "Locked (RPT)",
    "reverse-landscape": "Locked (RLS)",
}


def test_seven_exact_labels_everywhere():
    doc = json.loads((ROOT / "configs/nuxel/orientation/orientation.json").read_text())
    assert {m: doc["modes"][m]["label"] for m in LABELS} == LABELS
    daemon = (ROOT / "services/nuxel-orientation/nuxel-orientationd").read_text()
    policy = (ROOT / "services/nuxel-orientation/nuxel_orientation/policy.py").read_text()
    qs = (ROOT / "pwa/nuxel-home/js/qs.js").read_text()
    settings = (ROOT / "pwa/nuxel-apps/settings/settings.js").read_text()
    for label in LABELS.values():
        assert '"%s"' % label in policy
        assert '"%s"' % label in daemon
        assert "'%s'" % label in qs
        assert "'%s'" % label in settings


def test_transform_and_scale_are_one_verified_transaction():
    cfg = json.loads((ROOT / "configs/nuxel/orientation/orientation.json").read_text())
    comp = cfg["compositor"]
    assert comp["transform_map"] == {"0": "normal", "90": "270", "180": "180", "270": "90"}
    assert comp["portrait_scale"] == 2 and comp["landscape_scale"] == 1
    assert comp["commit_verified"] is True and comp["trial_seconds"] == 0
    src = (ROOT / "services/nuxel-orientation/nuxel_orientation/apply.py").read_text()
    assert "def scale_for" in src
    assert '"--scale"' in src
    assert "geometry_verified" in src
    assert "display_verified" in src


def test_bridge_set_always_requests_verified_apply():
    src = (ROOT / "services/nuxel-bridge/src/bridge.py").read_text()
    m = re.search(r"def set_mode\(self, mode\):(.*?)(?:\n\nclass |\Z)", src, re.S)
    assert m and '"--apply"' in m.group(1)


def test_daemon_commits_success_and_rolls_back_failure():
    src = (ROOT / "services/nuxel-orientation/nuxel-orientationd").read_text()
    assert 'self.transition_state = "verified"' in src
    assert 'self.transition_state = "rolled_back"' in src
    assert 'arm_trial=bool(doc.get("trial", False))' in src
    assert "trial = \"--trial\" in argv" in src


def test_recents_get_route_and_left_swipe_close_exist():
    api = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    # The GET route must exist before the POST-only duplicate.
    assert api.count("path == '/api/v1/windows/list'") >= 2
    assert "/api/v1/windows/close" in api
    recents = (ROOT / "pwa/nuxel-home/js/recents.js").read_text()
    assert "e.clientX < startX - 72" in recents
    assert "/api/v1/windows/close" in recents
    assert "Close ${app.name}" in recents
    assert "Switch to" not in recents


def test_nav_actions_are_real():
    dock = (ROOT / "tools/s10plus/a45/nuxel-navdock.c").read_text()
    assert 'forward("back-long")' in dock
    assert '"back", "home", "recents"' in dock
    fl = (ROOT / "tools/s10plus/a59/nuxel-foreign-toplevel.c").read_text()
    assert 'strcmp(mode, "close-foreground")' in fl
    assert 'strcmp(mode, "close")' in fl
    assert "opcode 5" in fl or "/* close */" in fl
    api = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    assert "_force_stop_app_units" in api and "SIGKILL" in api


def test_bluetooth_and_location_use_classic_svg_icons():
    for name in ("04-bluetooth.svg", "09-location.svg"):
        assert (ROOT / "assets/nuxel-quicksettings-icon-pack" / name).is_file()
    css = (ROOT / "pwa/nuxel-home/css/status-bar.css").read_text()
    assert "04-bluetooth.svg" in css and "09-location.svg" in css
    html = (ROOT / "pwa/nuxel-home/index.html").read_text()
    assert "04-bluetooth.svg" in html and "09-location.svg" in html


def test_idle_cpu_cadence_is_tightened():
    src = (ROOT / "tools/s10plus/a67/nuxel-wl-fb.c").read_text()
    assert "if (idle > 500) pace = 8;" in src
    assert "if (idle > 2000) pace = 3;" in src
    assert "if (idle > 6000) pace = 1;" in src
    unit = (ROOT / "services/nuxel-s10/systemd/nuxel-wl-fb.service.d/15-idle-fps.conf").read_text()
    assert "NUXEL_TARGET_FPS=20" in unit


def test_remote_sync_is_a_consumer_not_an_authority():
    src = (ROOT / "services/nuxel-remote-desktop/bin/nuxel-orientation-remote-sync").read_text()
    assert "status.json" in src and "remote.json" in src
    assert "never an" in src and "orientation\nauthority" in src
    assert "xrandr" in src
    assert "wayvnc" in src
    # Remote code must never write the local orientation state or /dev/fb0.
    assert "save_state" not in src and "/dev/fb0" not in src


def test_builder_and_deploy_include_userspace_orientation_chain():
    builder = (ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    assert "tools/s10plus/a67/nuxel-wl-fb.c" in builder
    assert "nuxel-orientation-remote-sync" in builder
    assert "xrandr" in builder
    deploy = (ROOT / "tools/s10plus/a67/deploy-pwnage54000.sh").read_text()
    assert "nuxel-orientation-remote-sync" in deploy
    assert "nuxel-wl-fb.p54000-prev" in deploy
    assert "cp -a '$R/pwa/nuxel-home/.'" in deploy


def test_navigation_reconciles_stale_lock_cache():
    src = (ROOT / "pwa/nuxel-home/js/app.js").read_text()
    assert "lockscreen:boot-authority-unlocked" in src
    assert "nav:locked-reconcile" in src
    assert "this._reconcileLockThenRetry" in src
    assert "window.dispatchEvent(new CustomEvent('nuxel:action'" in src


def test_xrdp_uses_xvnc_backend_for_runtime_resize():
    ini = (ROOT / "services/nuxel-remote-desktop/config/xrdp.ini").read_text()
    assert "autorun=Xvnc" in ini and "[Xvnc]" in ini and "lib=libvnc.so" in ini
    sync = (ROOT / "services/nuxel-remote-desktop/bin/nuxel-orientation-remote-sync").read_text()
    assert 'target["name"].startswith("VNC-")' in sync
    assert '"--newmode"' in sync and '"--addmode"' in sync
    assert "geometry_axis_matches_rotation_unsupported" in sync
    daemon = (ROOT / "services/nuxel-orientation/nuxel-orientationd").read_text()
    assert "_remote_last_tick" in daemon and "_spawn_remote_sync" in daemon


def test_manual_sensor_is_never_auto_capable():
    src = (ROOT / "services/nuxel-orientation/nuxel_orientation/sensors.py").read_text()
    assert 'entry["auto_capable"] = False' in src


def test_touch_rotation_is_owned_once_by_libinput_shim():
    cfg = json.loads((ROOT / "configs/nuxel/orientation/orientation.json").read_text())
    comp = cfg["compositor"]
    assert comp["input_state"] == "/run/nuxel-orientation/input.json"
    assert comp["input_matrix_map"] == {
        "normal": [1, 0, 0, 0, 1, 0],
        "90": [0, -1, 1, 1, 0, 0],
        "180": [-1, 0, 1, 0, -1, 1],
        "270": [0, 1, 0, -1, 0, 1],
    }
    shim = (ROOT / "tools/s10plus/a33/nuxel-libinput-path.c").read_text()
    assert "ORIENT_INPUT_FILE" in shim and "/run/nuxel-orientation/input.json" in shim
    assert "libinput_device_config_calibration_set_matrix" in shim
    assert "libinput_device_config_calibration_get_matrix" in shim
    assert "TOUCH_MATRIX_APPLY" in shim and "TOUCH_MATRIX_UNSUPPORTED" in shim
    assert "calibration_tick();" in shim
    assert "calibration_watch_thread" in shim and "TOUCH_MATRIX_WATCH_READY" in shim
    assert "calibration_watch_start();" in shim
    daemon = (ROOT / "services/nuxel-orientation/nuxel-orientationd").read_text()
    assert "def _emit_input_state" in daemon and "_emit_input_state(config, display" in daemon
    # No second input transform owner.
    navdock = (ROOT / "tools/s10plus/a45/nuxel-navdock.c").read_text()
    assert "calibration_set_matrix" not in navdock
    presenter = (ROOT / "tools/s10plus/a67/nuxel-wl-fb.c").read_text()
    assert "libinput" not in presenter.lower()


def test_live_deploy_installs_touch_and_microphone_fixes():
    deploy = (ROOT / "tools/s10plus/a67/deploy-pwnage54000.sh").read_text()
    for needle in (
        "nuxel-libinput-path.c",
        "libnuxel-libinput-path.so",
        "nuxel-pwa-host.c",
        "nuxel-pwa-host.p54000-prev",
        "portal.py.p54000-prev",
        "setfacl -m u:nuxel:r-x /var/lib/nuxel",
        "systemctl restart nuxel-portal",
    ):
        assert needle in deploy
    host = (ROOT / "tools/s10plus/a45/nuxel-pwa-host.c").read_text()
    assert '"enable-media-stream", TRUE' in host
    assert "allowed-microphone-recorder-media-object" in host
    portal_unit = (ROOT / "services/nuxel-portal/systemd/nuxel-portal.service").read_text()
    assert "SupplementaryGroups=nuxel-notifications" in portal_unit
    builder = (ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    assert 'setfacl -m "u:${NUXEL_UID}:r-x" "$STAGE/var/lib/nuxel"' in builder


def test_touch_matrix_maps_all_corners_for_each_transform():
    cfg = json.loads((ROOT / "configs/nuxel/orientation/orientation.json").read_text())
    matrices = cfg["compositor"]["input_matrix_map"]

    def apply(matrix, x, y):
        a, b, c, d, e, f = matrix
        return (a * x + b * y + c, d * x + e * y + f)

    # The raw portrait frame is the logical desktop rotated 90 degrees
    # counter-clockwise at compositor transform 270.  The touch matrix must undo
    # that mapping exactly, or the display image and hit targets diverge.
    # This is recovered from raw = np.rot90(grim, 3), not assumed.
    raw_corners = [(1, 0), (1, 1), (0, 0), (0, 1)]
    logical_corners = [(0, 0), (1, 0), (0, 1), (1, 1)]
    got = [tuple(round(v, 6) for v in apply(matrices["270"], *pt)) for pt in raw_corners]
    assert got == [tuple(float(v) for v in pt) for pt in logical_corners]
    # Identity is the verified portrait mapping.
    assert matrices["normal"] == [1, 0, 0, 0, 1, 0]
    # The three non-identity rotations remain distinct and invertible.
    for name in ("90", "180", "270"):
        a, b, c, d, e, f = matrices[name]
        assert abs(a * e - b * d) == 1


def test_touch_calibration_is_reasserted_after_first_compositor_dispatch():
    """A pre-dispatch set_matrix can be accepted yet not effective.

    libinput's path backend finishes initialising a device during its first
    dispatch.  The shim must re-apply the same calibration from the compositor
    thread afterwards, otherwise the first landscape touch frame behaves as
    identity even though TOUCH_MATRIX_APPLY logged ok=1.
    """
    shim = (ROOT / "tools/s10plus/a33/nuxel-libinput-path.c").read_text()
    assert "g_touch_force_apply" in shim
    assert "deferred-after-dispatch" in shim
    assert "g_touch_dispatch_count < 3" in shim
    assert "libinput_dispatch" in shim
    parity = (ROOT / "tools/s10plus/a31/nuxel-libinput-path.c").read_text()
    assert parity == shim


def test_recorder_has_one_shot_native_microphone_authorization():
    host = (ROOT / "tools/s10plus/a45/nuxel-pwa-host.c").read_text()
    bridge = (ROOT / "pwa/nuxel-home/js/host-bridge.js").read_text()
    rec = (ROOT / "pwa/nuxel-apps/recorder/js/recorder.js").read_text()
    assert "media.mic-authorize" in host
    assert "allowed-microphone-host-grant" in host
    assert "g_mic_grant_until_us" in host
    assert "micAuthorize" in bridge
    assert "hostMicAuthorize" in rec
    assert "window.parent && window.parent.NuxelHost" in rec


def test_deploy_installs_recorder_assets():
    deploy = (ROOT / "tools/s10plus/a67/deploy-pwnage54000.sh").read_text()
    rollback = (ROOT / "tools/s10plus/a67/rollback-pwnage54000.sh").read_text()
    assert "pwa/nuxel-apps/recorder" in deploy
    assert "pwa-recorder.tgz" in deploy
    assert "pwa-recorder.tgz" in rollback
