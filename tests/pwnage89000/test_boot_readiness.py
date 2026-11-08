#!/usr/bin/env python3
"""PWNAGE-89000 boot-readiness and durable-cue contracts (offline)."""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(errors="replace")


def load_soundd(tmp_path, monkeypatch):
    monkeypatch.setenv("NUXEL_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("NUXEL_SOUND_LIBRARY", str(tmp_path / "shared"))
    monkeypatch.setenv("NUXEL_SOUND_ASSIGNMENTS", str(tmp_path / "assignments.json"))
    monkeypatch.setenv("NUXEL_SOUND_PROBE_CACHE", str(tmp_path / "probe-cache.json"))
    monkeypatch.setenv("NUXEL_SOUND_QUEUE", str(tmp_path / "durable-queue.json"))
    monkeypatch.setenv("NUXEL_SOUNDD_SOCKET", str(tmp_path / "soundd.sock"))
    monkeypatch.setenv("NUXEL_RUNTIME", str(tmp_path / "run"))
    monkeypatch.setenv("NUXEL_PW_RUNTIME", str(tmp_path / "pw"))
    monkeypatch.setenv("NUXEL_SOUNDD_LOG", str(tmp_path / "soundd.log"))
    spec = importlib.util.spec_from_file_location(
        "nuxel_soundd_p89000_%d" % time.time_ns(),
        ROOT / "services/nuxel-sound/nuxel-soundd.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def load_clockd(tmp_path, monkeypatch):
    monkeypatch.setenv("NUXEL_CLOCK_STATE_FILE", str(tmp_path / "clock-state.json"))
    monkeypatch.setenv("NUXEL_CLOCK_STATE", str(tmp_path / "clockd.state"))
    monkeypatch.setenv("NUXEL_CLOCK_SOCKET", str(tmp_path / "clockd.sock"))
    monkeypatch.setenv("NUXEL_CLOCK_SCHEDULE", str(tmp_path / "legacy.json"))
    monkeypatch.setenv("NUXEL_CLOCK_WAKEALARM", str(tmp_path / "no-wakealarm"))
    monkeypatch.setenv("NUXEL_HAPTICS_FIFO", str(tmp_path / "no-haptics"))
    monkeypatch.setenv("NUXEL_NOTIFY", str(tmp_path / "no-notify"))
    monkeypatch.setenv("NUXEL_SOUNDD_SOCKET", str(tmp_path / "soundd.sock"))
    spec = importlib.util.spec_from_file_location(
        "nuxel_clockd_p89000_%d" % time.time_ns(),
        ROOT / "services/nuxel-clock/nuxel-clockd.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    mod.SOUNDCTL = "/bin/true"
    return mod


def test_soundd_unit_has_fast_truthful_readiness_contract():
    unit = read("services/nuxel-sound/nuxel-soundd.service")
    active = "\n".join(line for line in unit.splitlines()
                        if not line.lstrip().startswith("#"))
    assert "Type=notify" in active
    assert "NotifyAccess=main" in active
    assert "After=local-fs.target\n" in active
    assert "After=local-fs.target nuxel-audio-session.service" not in active
    assert "ExecStartPre=-/usr/lib/nuxel/nuxel-audio-route.sh --wait 200" not in active
    assert "ExecStartPre=/usr/libexec/nuxel/install-sound-library" in active


def test_audio_session_and_mic_route_are_not_direct_boot_target_consumers():
    audio = read("services/nuxel-s10/systemd/nuxel-audio-session.service")
    mic = read("services/nuxel-s10/systemd/nuxel-mic-route.service")
    path = read("services/nuxel-s10/systemd/nuxel-mic-route.path")
    assert "WantedBy=multi-user.target" not in audio
    assert "WantedBy=multi-user.target" not in mic
    # The pending state document is written before the route is usable; only
    # the applied-ready receipt may trigger the microphone route.
    assert "PathChanged=/run/nuxel-audio-route.ready" in path
    assert "PathExists=/run/nuxel-audio-route.ready" not in path
    assert "Unit=nuxel-mic-route.service" in path
    active_mic = "\n".join(line for line in mic.splitlines()
                            if not line.lstrip().startswith("#"))
    assert "--wait 180" not in active_mic
    assert "ExecStart=/usr/lib/nuxel/nuxel-mic-route.sh\n" in active_mic


def test_audio_session_waits_for_pipewire_core_and_supervises_wireplumber():
    src = read("services/nuxel-s10/bin/nuxel-audio-session.sh")
    # A socket inode is not enough: WirePlumber previously exited with
    # "Failed to connect to PipeWire" and the default sink/source metadata was
    # missing for the whole boot (no cues, 0/100% volume steps, monitor mic).
    assert "pw-cli info 0" in src
    assert "PipeWire:Interface:Core" in src
    assert "start_wireplumber()" in src
    assert "wireplumber exited rc=" in src
    assert "pkill -TERM -x wireplumber" in src


def test_audio_route_retries_default_sink_metadata():
    src = read("services/nuxel-s10/bin/nuxel-audio-route.sh")
    assert "WirePlumber default-node metadata unavailable" in src
    assert "pactl set-default-sink" in src
    assert "while [ \"$n\" -lt 40 ]" in src


def test_static_launcher_and_radio_state_do_not_serialize_the_compositor():
    web = read("services/nuxel-web.service")
    active_web = "\n".join(line for line in web.splitlines()
                            if not line.lstrip().startswith("#"))
    assert "Wants=nuxel-http-bridge.service" in active_web
    assert "After=nuxel-http-bridge.service" not in active_web
    interface = read("services/nuxel-s10/systemd/nuxel-interface-state.service")
    active_if = "\n".join(line for line in interface.splitlines()
                           if not line.lstrip().startswith("#"))
    assert "WantedBy=multi-user.target" in active_if
    assert "Before=nuxel-wayland.service" not in active_if


def test_sound_worker_does_not_spawn_without_backend_readiness():
    src = read("services/nuxel-sound/nuxel-soundd.py")
    assert "def _pw_socket_ready" in src
    assert "def _route_pending" in src
    assert 'Path(PW_RUNTIME, "pipewire-0").is_socket()' in src
    assert "state=applied" in src and "calliope=MUB0" in src
    assert "if not self._pw_socket_ready():" in src
    assert "if self._route_pending():" in src
    # The old write path reset the backoff deadline to zero on every failure.
    assert "self._last_start_attempt = 0.0\n            self._start_backoff" not in src
    assert src.count("if not self._pw_socket_ready():") >= 2


def test_sound_player_deduplicates_token_retries():
    mod = load_soundd(Path("/tmp"), type("M", (), {
        "setenv": staticmethod(lambda *args: None)})())
    player = mod.SoundPlayer()
    cue = {"action": "alarm", "token": "occ-1", "pcm": b"\0\0", "loop": True}
    assert player.play(cue) is True
    assert player.play(dict(cue)) is False
    player.stop("occ-1")


def test_soundd_durable_queue_survives_restart(tmp_path, monkeypatch):
    mod = load_soundd(tmp_path, monkeypatch)
    manager = mod.SoundManager()
    manager._persist_durable_cue("occ-durable", "alarm",
                                 str(tmp_path / "alarm.mp3"), True)
    doc = json.loads((tmp_path / "durable-queue.json").read_text())
    assert doc["cues"][0]["token"] == "occ-durable"
    manager.stop_cue("occ-durable", "alarm")
    doc = json.loads((tmp_path / "durable-queue.json").read_text())
    assert doc["cues"] == []


def test_clockd_retries_same_token_and_rearms_on_restart(tmp_path, monkeypatch):
    mod = load_clockd(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    occ = daemon._occurrence(kind="alarm", alarm_id="a", key="k",
                             label="Wake", due_ms=mod._now_ms(), state="snoozed")
    daemon.state["occurrences"].append(occ)
    daemon._fire(occ)
    assert occ["cue_state"] == "pending"

    replies = [
        {"success": False, "error": "soundd-unavailable"},
        {"success": True, "queued": True, "duplicate": False,
         "player": {"instance_id": "soundd-A", "active_token": occ["token"]}},
    ]
    seen = []

    def fake_soundctl(*args, **kwargs):
        seen.append(list(args))
        return replies.pop(0)

    daemon._soundctl = fake_soundctl
    daemon._cue_send(occ["id"])
    assert occ["cue_state"] == "pending"
    assert occ["cue_attempts"] == 1
    daemon._cue_send(occ["id"])
    assert occ["cue_state"] == "accepted"
    assert occ["soundd_instance"] == "soundd-A"
    assert seen[0] == seen[1]
    assert "--token" in seen[0]

    restarted = mod.ClockDaemon()
    reread = next(o for o in restarted.state["occurrences"] if o["id"] == occ["id"])
    assert reread["cue_state"] == "pending"
    assert reread["cue_attempts"] == 0

def test_boot_cue_is_event_driven_and_runs_once():
    svc = read("services/nuxel-session/systemd/nuxel-boot-sound.service")
    path = read("services/nuxel-session/systemd/nuxel-boot-sound.path")
    active_svc = "\n".join(line for line in svc.splitlines()
                            if not line.lstrip().startswith("#"))
    assert "ConditionPathExists=/run/nuxel-audio-route.ready" in active_svc
    assert "ConditionPathExists=!/run/nuxel-boot-sound.played" in active_svc
    assert "WantedBy=nuxel-wayland.service" not in active_svc
    assert "PathChanged=/run/nuxel-audio-route.ready" in path
    assert "PathExists=/run/nuxel-audio-route.ready" not in path
    assert "Unit=nuxel-boot-sound.service" in path
    assert "WantedBy=paths.target" in path

def test_device_permissions_do_not_gate_the_compositor():
    unit = read("services/nuxel-s10/systemd/nuxel-device-permissions.service")
    active = "\n".join(line for line in unit.splitlines()
                        if not line.lstrip().startswith("#"))
    assert "Before=nuxel-audio-route.service nuxel-bluetooth.service" in active
    assert "nuxel-wayland.service" not in active
