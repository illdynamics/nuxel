#!/usr/bin/env python3
"""Offline execution tests for the PWNAGE-31000 preload controller.

A fake mpv peer implements just enough of the real IPC contract to exercise the
controller's timing, readiness, failure and cleanup paths.  These tests are
mocked process/IPC tests, not physical-device evidence.
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "services/nuxel-preload-cinema/nuxel-preload-cinema"
SUPPLIED_ASSET = ROOT / "assets/nuxel-preloading-screen.mp4"
EXISTING_MP4 = ROOT / "assets/nuxel-boot-animation.mp4"

# The controller is exercised offline on macOS too.  These tests inspect or
# depend on Linux boot facts (/proc uptime, boot_id, process table); they remain
# authoritative on the handset, but must not report a false failure merely
# because the dev host has no /proc.
LINUX_PROC = Path("/proc").is_dir()
linux_only = pytest.mark.skipif(not LINUX_PROC, reason="requires Linux /proc")

FAKE_MPV = r'''#!/usr/bin/env python3
import json, os, signal, socket, sys, time

args = sys.argv[1:]
args_file = os.environ.get("FAKE_MPV_ARGS_FILE")
if args_file:
    with open(args_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(args) + "\n")

def arg(prefix):
    for item in args:
        if item.startswith(prefix):
            return item[len(prefix):]
    return None

if "--vo=null" in args or "--frames=1" in args:
    code = int(os.environ.get("FAKE_MPV_PREFLIGHT_EXIT", "0"))
    if os.environ.get("FAKE_MPV_PREFLIGHT_STDERR"):
        sys.stderr.write(os.environ["FAKE_MPV_PREFLIGHT_STDERR"])
    sys.exit(code)

ipc_path = arg("--input-ipc-server=")
if not ipc_path:
    sys.exit(9)
if os.environ.get("FAKE_MPV_IP_FAIL") == "1":
    time.sleep(5)
    sys.exit(0)

try:
    os.unlink(ipc_path)
except OSError:
    pass
os.makedirs(os.path.dirname(ipc_path), exist_ok=True)
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(ipc_path)
server.listen(1)
server.settimeout(5.0)

def stop(*_a):
    try:
        server.close()
    except OSError:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

try:
    conn, _ = server.accept()
except OSError:
    sys.exit(0)
conn.settimeout(0.1)
eof_ms = int(os.environ.get("FAKE_MPV_EOF_MS", "150"))
exit_ms = int(os.environ.get("FAKE_MPV_PLAYBACK_EXIT_MS", "0"))
started = time.monotonic()
buf = b""
eof = False
paused = False
while True:
    now = time.monotonic()
    if not eof and (now - started) * 1000 >= eof_ms:
        eof = True
    if exit_ms and (now - started) * 1000 >= exit_ms:
        sys.exit(2)
    try:
        data = conn.recv(4096)
    except socket.timeout:
        continue
    except OSError:
        break
    if not data:
        break
    buf += data
    while b"\n" in buf:
        line, _, buf = buf.partition(b"\n")
        try:
            req = json.loads(line.decode("utf-8", "replace"))
        except ValueError:
            continue
        rid = req.get("request_id")
        cmd = req.get("command") or []
        if cmd[:1] == ["get_property"] and cmd[1:2] == ["eof-reached"]:
            reply = {"request_id": rid, "error": "success", "data": bool(eof)}
        elif cmd[:1] == ["get_property"] and cmd[1:2] == ["playback-time"]:
            reply = {"request_id": rid, "error": "success", "data": 0.05}
        elif cmd[:1] == ["set_property"] and cmd[1:2] == ["pause"]:
            paused = bool(cmd[2]) if len(cmd) > 2 else False
            reply = {"request_id": rid, "error": "success", "data": None}
        elif cmd[:1] == ["quit"]:
            try:
                conn.sendall((json.dumps({"request_id": rid, "error": "success"}) + "\n").encode())
            except OSError:
                pass
            sys.exit(0)
        else:
            reply = {"request_id": rid, "error": "success", "data": None}
        try:
            conn.sendall((json.dumps(reply) + "\n").encode())
        except OSError:
            sys.exit(0)
'''


class Harness:
    def __init__(self, tmp_path: Path, *, asset: bool = True, ready: bool = True,
                 boot_os: bool = True, wlfb: bool = True, display_on: bool = True,
                 touch: bool = True, extra_config: dict | None = None):
        self.tmp = tmp_path
        self.asset = tmp_path / "nuxel-preloading-screen.mp4"
        if asset:
            # Prefer the real PWNAGE-31000 clip so the controller exercises its
            # own duration parser and hash path; the fake mpv does not decode it.
            if SUPPLIED_ASSET.is_file():
                self.asset.symlink_to(SUPPLIED_ASSET)
            elif EXISTING_MP4.is_file():
                self.asset.symlink_to(EXISTING_MP4)
            else:
                self.asset.write_bytes(b"not-a-real-mp4")
        self.launcher_ready = tmp_path / "nuxel-launcher-ready"
        self.home_state = tmp_path / "nuxel-home.state"
        self.wlfb_state = tmp_path / "nuxel-wl-fb.state"
        self.display_state = tmp_path / "display"
        self.touch_state = tmp_path / "nuxel-touch-arm.state"
        self.session_owner = tmp_path / "nuxel-preload-session.owner"
        self.session_log = tmp_path / "nuxel-session.log"
        self.runtime = tmp_path / "run"
        self.runtime.mkdir(exist_ok=True)
        self.lock = self.runtime / "preload-cinema.lock"
        self.receipt = self.runtime / "preload-cinema.receipt"
        self.log = tmp_path / "preload-cinema.log"
        self.done = self.runtime / "preload-cinema.done"
        self.overlay = self.runtime / "preload-cinema.overlay"
        self.status = tmp_path / "docroot-preload-status.json"
        self.config = tmp_path / "preload-cinema.json"
        self.fake_mpv = tmp_path / "fake-mpv"
        self.fake_mpv.write_text(FAKE_MPV, encoding="utf-8")
        self.fake_mpv.chmod(0o755)
        self.args_file = tmp_path / "fake-mpv-args.jsonl"
        self.wayland = tmp_path / "wayland"
        self.wayland.mkdir(exist_ok=True)
        (self.wayland / "wayland-0").write_text("", encoding="utf-8")
        if ready:
            self.launcher_ready.write_text("ready\n", encoding="utf-8")
        if boot_os:
            self.home_state.write_text(
                "NUXEL_HOME_BOOT_OWNER os_animation=1\n"
                "NUXEL_HOME_OPEN url=http://127.0.0.1:8000/pwa/nuxel-home/index.html?boot=os\n",
                encoding="utf-8")
        else:
            self.home_state.write_text(
                "NUXEL_HOME_OPEN url=http://127.0.0.1:8000/pwa/nuxel-home/index.html\n",
                encoding="utf-8")
        if wlfb:
            display = "on" if display_on else "off"
            self.wlfb_state.write_text(
                "FRAMES_OK total=10 fps_1s=10 failures=0 owner=nuxel-wl-fb "
                "display=%s out=720x1520\n" % display, encoding="utf-8")
            # The persistent receipt is the fresh-boot authority (the /run line
            # can remain DISPLAY_SLEEP on a static lockscreen).
            self.display_state.write_text(
                "DISPLAY_%s\nbrightness=12800\nbl_power=0\nowner=nuxel-wl-fb\n"
                % ("ON" if display_on else "OFF"), encoding="utf-8")
        if touch:
            self.touch_state.write_text("2026-10-28T09:00:00Z ARMED_OK path=/dev/input/event2\n",
                                        encoding="utf-8")
        cfg = {
            "schema_version": 1,
            "enabled": True,
            "asset": str(self.asset),
            "asset_sha256": None,
            "player": str(self.fake_mpv),
            "video_output": "wlshm",
            "max_display_ms": 2000,
            "start_timeout_ms": 1500,
            "readiness_grace_ms": 0,
            "hard_timeout_ms": 5000,
            "poll_ms": 40,
            "preflight_timeout_ms": 1500,
            "require_boot_os": True,
            "audio": "never",
        }
        if extra_config:
            cfg.update(extra_config)
        self.config.write_text(json.dumps(cfg), encoding="utf-8")

    def env(self, **overrides):
        env = dict(os.environ)
        env.update({
            "NUXEL_PRELOAD_CONFIG": str(self.config),
            "NUXEL_PRELOAD_ASSET": str(self.asset),
            "NUXEL_PRELOAD_MPV": str(self.fake_mpv),
            "NUXEL_PRELOAD_RUNTIME_DIR": str(self.runtime),
            "NUXEL_PRELOAD_LOCK": str(self.lock),
            "NUXEL_PRELOAD_RECEIPT": str(self.receipt),
            "NUXEL_PRELOAD_LOG": str(self.log),
            "NUXEL_PRELOAD_DONE": str(self.done),
            "NUXEL_PRELOAD_OVERLAY": str(self.overlay),
            "NUXEL_PRELOAD_STATUS": str(self.status),
            "NUXEL_PRELOAD_HOME_STATE": str(self.home_state),
            "NUXEL_PRELOAD_LAUNCHER_READY": str(self.launcher_ready),
            "NUXEL_PRELOAD_WLFB_STATE": str(self.wlfb_state),
            "NUXEL_PRELOAD_DISPLAY_STATE": str(self.display_state),
            "NUXEL_PRELOAD_TOUCH_STATE": str(self.touch_state),
            "NUXEL_PRELOAD_SESSION_OWNER": str(self.session_owner),
            "NUXEL_PRELOAD_SESSION_LOG": str(self.session_log),
            "NUXEL_PRELOAD_WAYLAND_RUNTIME": str(self.wayland),
            "NUXEL_PRELOAD_WAYLAND_DISPLAY": "wayland-0",
            "FAKE_MPV_ARGS_FILE": str(self.args_file),
        })
        env.update({k: str(v) for k, v in overrides.items()})
        return env

    def run(self, timeout=8, **overrides):
        return subprocess.run([sys.executable, str(CONTROLLER)], env=self.env(**overrides),
                              capture_output=True, text=True, timeout=timeout)

    def receipt_doc(self):
        return json.loads(self.receipt.read_text(encoding="utf-8"))

    def overlay_doc(self):
        return json.loads(self.overlay.read_text(encoding="utf-8"))

    def args(self):
        if not self.args_file.is_file():
            return []
        return [json.loads(line) for line in self.args_file.read_text().splitlines() if line]

    def playback_args(self):
        return [a for a in self.args() if any(x.startswith("--input-ipc-server=") for x in a)]


def test_successful_play_and_cleanup(tmp_path):
    h = Harness(tmp_path, extra_config={"max_display_ms": 3000, "hard_timeout_ms": 5000})
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["reason"] == "video-and-lockscreen-ready"
    assert r["video_eof"] is True
    assert r["readiness"]["ready"] is True
    assert r["unlock_actions"] == 0
    assert r["audio"] == "disabled"
    args = h.playback_args()[0]
    for needle in ("--no-audio", "--mute=yes", "--fullscreen", "--osc=no",
                   "--input-default-bindings=no", "--keepaspect=yes", "--panscan=0",
                   "--vo=wlshm", "--keep-open=yes", "--idle=yes"):
        assert needle in args
    assert not (h.runtime / "preload-cinema.sock").exists()


def test_overlay_cover_marker_is_published_before_release(tmp_path):
    h = Harness(tmp_path, extra_config={"max_display_ms": 4000, "hard_timeout_ms": 6000})
    env = h.env(FAKE_MPV_EOF_MS="1200")
    proc = subprocess.Popen([sys.executable, str(CONTROLLER)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    seen = None
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            doc = h.overlay_doc()
        except (OSError, ValueError):
            doc = {}
        if doc.get("state") == "covered":
            seen = doc
            break
        time.sleep(0.04)
    out, err = proc.communicate(timeout=8)
    assert proc.returncode == 0, err
    assert seen is not None, "first-frame cover state was never published"
    assert seen["state"] == "covered"
    assert seen["first_frame_s"] > 0
    final = h.overlay_doc()
    assert final["state"] in ("covered", "done")
    served = json.loads(h.status.read_text(encoding="utf-8"))
    assert served["state"] in ("covered", "done")
    if Path("/proc/sys/kernel/random/boot_id").is_file():
        assert served["boot_id"]


def test_missing_asset_publishes_fallback_overlay_marker(tmp_path):
    h = Harness(tmp_path, asset=False)
    out = h.run()
    assert out.returncode == 0, out.stderr
    doc = h.overlay_doc()
    assert doc["state"] == "fallback"
    assert doc["reason"] in ("asset-missing", "exited-before-first-frame")


def test_supplied_asset_mp4_parser_returns_real_duration():
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("npc_test_parse", str(CONTROLLER))
    spec = importlib.util.spec_from_loader("npc_test_parse", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["npc_test_parse"] = module
    loader.exec_module(module)
    assert abs((module.mp4_duration_seconds(SUPPLIED_ASSET) or 0) - 6.016) < 0.05


def test_supplied_asset_audio_is_never_enabled(tmp_path):
    h = Harness(tmp_path)
    out = h.run()
    assert out.returncode == 0, out.stderr
    args = h.playback_args()[0]
    assert "--no-audio" in args
    assert "--mute=yes" in args
    assert not any(a.startswith("--audio-file") or a.startswith("--aid") for a in args)


def test_readiness_before_video_completion_waits_for_eof(tmp_path):
    h = Harness(tmp_path, extra_config={"max_display_ms": 4000, "hard_timeout_ms": 6000})
    t0 = time.monotonic()
    out = h.run(FAKE_MPV_EOF_MS="600")
    elapsed = time.monotonic() - t0
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["video_eof"] is True
    assert elapsed >= 0.55


def test_video_completion_before_readiness_holds_until_ready(tmp_path):
    h = Harness(tmp_path, ready=False, extra_config={"max_display_ms": 4000,
                                                      "hard_timeout_ms": 7000})
    # No launcher-ready receipt at start; write it after the fake video EOF.
    env = h.env(FAKE_MPV_EOF_MS="120")
    proc = subprocess.Popen([sys.executable, str(CONTROLLER)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(0.75)
    h.launcher_ready.write_text("ready\n", encoding="utf-8")
    out, err = proc.communicate(timeout=8)
    assert proc.returncode == 0, err
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["video_eof"] is True
    assert r["readiness_ready_at_s"] is not None
    assert r["readiness_ready_at_s"] >= 0.25


def test_slow_critical_startup_is_bounded_and_logged(tmp_path):
    h = Harness(tmp_path, ready=False, extra_config={"max_display_ms": 400,
                                                      "hard_timeout_ms": 900,
                                                      "readiness_grace_ms": 0})
    out = h.run(FAKE_MPV_EOF_MS="80")
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["reason"] == "hard-timeout-readiness-pending"
    assert r["bounded"] is True
    assert r["readiness"]["ready"] is False
    assert "hard_timeout" in h.log.read_text()


def test_bound_pauses_moving_video_before_hard_timeout(tmp_path):
    h = Harness(tmp_path, ready=False, extra_config={"max_display_ms": 250,
                                                      "hard_timeout_ms": 800})
    out = h.run(FAKE_MPV_EOF_MS="5000")
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["bounded"] is True
    assert r["video_held"] is True
    assert r["reason"] == "hard-timeout-readiness-pending"
    assert "video_paused_at_bound" in h.log.read_text()


def test_noncritical_service_failure_does_not_block(tmp_path):
    # This failure is deliberately not part of the readiness input.  The
    # controller must ignore it just as the real controller ignores
    # NetworkManager-wait-online/Bluetooth/GNSS failures.
    h = Harness(tmp_path)
    (tmp_path / "NetworkManager-wait-online.failed").write_text("failed\n")
    out = h.run()
    assert out.returncode == 0, out.stderr
    assert h.receipt_doc()["verdict"] == "PLAYED"


def test_missing_asset_falls_back_without_spawning_player(tmp_path):
    h = Harness(tmp_path, asset=False)
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "FALLBACK"
    assert r["reason"] == "asset-missing"
    assert h.args() == []


def test_empty_asset_falls_back(tmp_path):
    h = Harness(tmp_path)
    h.asset.unlink()
    h.asset.write_bytes(b"")
    out = h.run()
    assert out.returncode == 0, out.stderr
    assert h.receipt_doc()["reason"] == "asset-empty"
    assert h.args() == []


def test_asset_hash_mismatch_falls_back(tmp_path):
    h = Harness(tmp_path, extra_config={"asset_sha256": "0" * 64})
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["reason"] == "asset-hash-mismatch"
    assert h.args() == []


def test_codec_or_decoder_preflight_failure_falls_back(tmp_path):
    h = Harness(tmp_path)
    out = h.run(FAKE_MPV_PREFLIGHT_EXIT="3", FAKE_MPV_PREFLIGHT_STDERR="decoder init failed")
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "FALLBACK"
    assert r["reason"] == "decode-failed:3"
    assert len(h.playback_args()) == 0


def test_player_missing_falls_back(tmp_path):
    h = Harness(tmp_path)
    h.fake_mpv.unlink()
    out = h.run()
    assert out.returncode == 0, out.stderr
    assert h.receipt_doc()["reason"] == "player-missing"


def test_ipc_failure_falls_back(tmp_path):
    h = Harness(tmp_path)
    out = h.run(FAKE_MPV_IP_FAIL="1", timeout=10)
    assert out.returncode == 0, out.stderr
    assert h.receipt_doc()["reason"] == "player-ipc-unavailable"


def test_playback_process_exit_falls_back_and_cleans_up(tmp_path):
    h = Harness(tmp_path)
    out = h.run(FAKE_MPV_PLAYBACK_EXIT_MS="100", FAKE_MPV_EOF_MS="5000", timeout=10)
    assert out.returncode == 0, out.stderr
    assert h.receipt_doc()["reason"] == "player-exited"
    assert not (h.runtime / "preload-cinema.sock").exists()


def test_display_not_ready_skips_playback(tmp_path):
    h = Harness(tmp_path, wlfb=False)
    out = h.run()
    assert out.returncode == 0, out.stderr
    assert h.receipt_doc()["reason"] == "display-not-ready"
    assert h.args() == []


def test_display_off_skips_playback(tmp_path):
    h = Harness(tmp_path, display_on=False)
    out = h.run()
    assert out.returncode == 0, out.stderr
    assert h.receipt_doc()["reason"] == "display-not-ready"


@linux_only
def test_static_screen_display_sleep_line_does_not_override_live_panel(tmp_path):
    # Measured on the S10+ at boot: /run/nuxel-wl-fb.state last said
    # "DISPLAY_SLEEP ... display=off" while /var/lib/nuxel/display said
    # DISPLAY_ON and the panel was lit.  The fresh persistent receipt wins.
    h = Harness(tmp_path)
    h.wlfb_state.write_text(
        "DISPLAY_SLEEP total=186 failures=0 owner=nuxel-wl-fb display=off capture=stopped\n",
        encoding="utf-8")
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["readiness"]["display_on"] is True
    assert r["readiness"]["wlfb_ready"] is True
    assert r["readiness"]["detail"]["display_state_fresh"] is True


@linux_only
def test_live_display_off_receipt_wins_over_frames_line(tmp_path):
    h = Harness(tmp_path)
    h.wlfb_state.write_text(
        "FRAMES_OK total=10 owner=nuxel-wl-fb display=on out=720x1520\n",
        encoding="utf-8")
    h.display_state.write_text(
        "DISPLAY_OFF\nbrightness=0\nbl_power=4\nowner=nuxel-wl-fb\n",
        encoding="utf-8")
    out = h.run()
    assert out.returncode == 0, out.stderr
    assert h.receipt_doc()["reason"] == "display-not-ready"


@linux_only
def test_stale_display_receipt_is_ignored(tmp_path):
    h = Harness(tmp_path)
    h.wlfb_state.write_text(
        "DISPLAY_SLEEP total=1 owner=nuxel-wl-fb display=off capture=stopped\n",
        encoding="utf-8")
    h.display_state.write_text(
        "DISPLAY_ON\nbrightness=12800\nowner=nuxel-wl-fb\n", encoding="utf-8")
    os.utime(h.display_state, (0, 0))
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["reason"] == "display-not-ready"
    assert r["readiness"]["detail"]["display_state_fresh"] is False


def test_late_display_handoff_is_waited_for_within_start_timeout(tmp_path):
    # The initramfs animation owns the panel for ~21 s on the S10+.  The
    # controller must not treat that as "display failed"; it waits for the
    # display gate and then plays, without adding a fixed delay once it is up.
    h = Harness(tmp_path, wlfb=False,
                extra_config={"start_timeout_ms": 4000, "max_display_ms": 3000,
                              "hard_timeout_ms": 5000})
    env = h.env(FAKE_MPV_EOF_MS="100")
    proc = subprocess.Popen([sys.executable, str(CONTROLLER)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(1.0)
    h.wlfb_state.write_text(
        "FRAMES_OK total=10 owner=nuxel-wl-fb display=on out=720x1520\n",
        encoding="utf-8")
    h.display_state.write_text(
        "DISPLAY_ON\nbrightness=12800\nowner=nuxel-wl-fb\n", encoding="utf-8")
    out, err = proc.communicate(timeout=8)
    assert proc.returncode == 0, err
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["reason"] == "video-and-lockscreen-ready"
    assert r["readiness"]["wlfb_ready"] is True


def test_vm_or_desktop_mode_never_overlays(tmp_path):
    h = Harness(tmp_path, boot_os=False)
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["reason"] == "not-os-boot-mode"
    assert h.args() == []


def test_second_run_in_same_boot_is_skipped_before_player(tmp_path):
    h = Harness(tmp_path)
    first = h.run()
    assert first.returncode == 0, first.stderr
    assert h.receipt_doc()["verdict"] == "PLAYED"
    assert h.done.is_file()
    calls_before = len(h.args())
    second = h.run()
    assert second.returncode == 0, second.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "ALREADY_RAN"
    assert r["reason"] == "one-shot-boot-marker-present"
    assert len(h.args()) == calls_before


def test_duplicate_instance_does_not_spawn_player(tmp_path):
    h = Harness(tmp_path)
    lock = h.lock.open("a+")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        out = h.run()
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
    assert out.returncode == 0, out.stderr
    assert h.receipt_doc()["verdict"] == "DUPLICATE"
    assert h.args() == []


def test_touch_unknown_becomes_settled_after_grace(tmp_path):
    h = Harness(tmp_path, touch=False,
                extra_config={"readiness_grace_ms": 100, "max_display_ms": 900,
                              "hard_timeout_ms": 1500})
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["readiness"]["touch_unknown"] is True


def test_touch_points_after_armed_ok_do_not_unsettle_readiness(tmp_path):
    h = Harness(tmp_path)
    h.touch_state.write_text(
        "2026-10-28T09:36:48Z ARMED_OK path=/dev/input/event2 name='sec_touchscreen'\n"
        "2026-10-28T09:46:26Z TOUCH_POINT slot=0 n=341\n"
        "2026-10-28T09:46:26Z TOUCH_POINT slot=0 n=342\n",
        encoding="utf-8")
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["readiness"]["touch_settled"] is True
    assert r["readiness"]["touch_unknown"] is False


def test_no_touch_device_is_an_honest_settled_state(tmp_path):
    h = Harness(tmp_path)
    h.touch_state.write_text("2026-10-28T09:00:00Z NO_TOUCH_DEVICE retry=3\n",
                             encoding="utf-8")
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["readiness"]["touch_settled"] is True


def test_no_post_readiness_delay(tmp_path):
    h = Harness(tmp_path, extra_config={"max_display_ms": 4000, "hard_timeout_ms": 6000})
    t0 = time.monotonic()
    out = h.run(FAKE_MPV_EOF_MS="100")
    elapsed = time.monotonic() - t0
    assert out.returncode == 0, out.stderr
    assert elapsed < 2.5


@linux_only
def test_no_player_process_survives_handoff(tmp_path):
    h = Harness(tmp_path)
    out = h.run()
    assert out.returncode == 0, out.stderr
    needle = str(h.fake_mpv)
    survivors = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", "replace")
        except OSError:
            continue
        if needle in cmdline:
            survivors.append((entry.name, cmdline[:160]))
    assert survivors == [], survivors


def test_early_mode_waits_for_launcher_and_display_before_start(tmp_path):
    # Early mode still races the launcher for stacking, but the one-shot clip
    # must not start until the display bridge owns the panel.  With both ready
    # the order is: launcher wait -> display wait -> player start.
    h = Harness(tmp_path, ready=True, boot_os=False, wlfb=True,
                display_on=True, touch=False,
                extra_config={"early_wait_launcher_ms": 250,
                              "early_map_delay_ms": 0,
                              "max_display_ms": 2000,
                              "hard_timeout_ms": 5000})
    out = h.run(NUXEL_PRELOAD_EARLY="1")
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["readiness"]["wlfb_ready"] is True
    assert r["readiness"]["display_on"] is True
    log = h.log.read_text(encoding="utf-8")
    assert "early_launcher_wait" in log and "ready=1" in log
    assert "early_display_wait" in log and "ready=1" in log
    assert log.index("early_launcher_wait") < log.index("early_display_wait")
    assert log.index("early_display_wait") < log.index("player_starting")


def test_early_mode_waits_for_the_display_bridge_before_playing(tmp_path):
    # Measured 2026-10-29 on the S10+: early mode spawned mpv while the
    # initramfs animation still owned /dev/fb0.  mpv reached playback-time
    # 5.958 s before the bridge published its first frame, so only the final
    # instant of the 6.016 s clip was ever on the glass.  Early mode must wait
    # for wlfb_ready + display_on (bounded) before it spends the one-shot clip.
    h = Harness(tmp_path, ready=True, boot_os=False, wlfb=False,
                display_on=False, touch=False,
                extra_config={"early_wait_launcher_ms": 250,
                              "start_timeout_ms": 4000,
                              "max_display_ms": 3000,
                              "hard_timeout_ms": 6000})
    env = h.env(NUXEL_PRELOAD_EARLY="1", FAKE_MPV_EOF_MS="150")
    proc = subprocess.Popen([sys.executable, str(CONTROLLER)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(0.9)
    # The display bridge is not ready yet: no playback may have started.
    assert h.playback_args() == []
    h.wlfb_state.write_text(
        "FRAMES_OK total=10 owner=nuxel-wl-fb display=on out=720x1520\n",
        encoding="utf-8")
    h.display_state.write_text(
        "DISPLAY_ON\nbrightness=12800\nowner=nuxel-wl-fb\n", encoding="utf-8")
    out, err = proc.communicate(timeout=8)
    assert proc.returncode == 0, err
    r = h.receipt_doc()
    assert r["verdict"] == "PLAYED"
    assert r["readiness"]["wlfb_ready"] is True
    log = h.log.read_text(encoding="utf-8")
    assert "early_display_wait" in log and "ready=1" in log


def test_early_mode_falls_back_if_the_display_never_arrives(tmp_path):
    h = Harness(tmp_path, ready=True, boot_os=False, wlfb=False,
                display_on=False, touch=False,
                extra_config={"early_wait_launcher_ms": 100,
                              "start_timeout_ms": 350,
                              "max_display_ms": 2000,
                              "hard_timeout_ms": 3000})
    out = h.run(NUXEL_PRELOAD_EARLY="1")
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "FALLBACK"
    assert r["reason"] == "display-not-ready"
    assert h.playback_args() == []


def test_early_mode_records_launcher_ready_before_player(tmp_path):
    h = Harness(tmp_path, ready=True, boot_os=False, wlfb=True,
                display_on=True, touch=False,
                extra_config={"early_wait_launcher_ms": 1000,
                              "max_display_ms": 2000,
                              "hard_timeout_ms": 5000})
    out = h.run(NUXEL_PRELOAD_EARLY="1")
    assert out.returncode == 0, out.stderr
    log = h.log.read_text(encoding="utf-8")
    assert "early_launcher_wait" in log and "ready=1" in log
    ready_at = log.index("early_launcher_wait")
    player_at = log.index("player_starting")
    assert ready_at < player_at


def test_controller_never_calls_unlock_or_opens_framebuffer(tmp_path):
    source = CONTROLLER.read_text(encoding="utf-8")
    assert 'action_perform("unlock"' not in source
    assert "system.action" not in source or "unlock" not in source.split("system.action", 1)[1][:200]
    # The only literal /dev/fb0 mention is documentation; there is no open().
    assert "open(\"/dev/fb0" not in source
    assert "open('/dev/fb0" not in source


def test_systemd_fallback_yields_to_session_without_done_marker(tmp_path):
    """The session owns the overlay; a fallback unit must not write .done."""
    h = Harness(tmp_path, ready=True)
    h.session_owner.write_text("", encoding="utf-8")
    out = h.run()
    assert out.returncode == 0, out.stderr
    r = h.receipt_doc()
    assert r["verdict"] == "YIELD_SESSION"
    assert not h.done.exists()
    assert "yield_session" in h.log.read_text(encoding="utf-8")
