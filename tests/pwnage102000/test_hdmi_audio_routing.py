"""PWNAGE-102000 HDMI/DisplayPort audio discovery and routing tests.

These tests use the real decoder for the Samsung ``edid_audio_informs()`` word
and a fake PipeWire backend.  They exercise the same state transitions the
live sound daemon runs; no test claims physical audibility.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "nuxel-sound"))

import nuxel_audio_outputs as ao  # noqa: E402

LIVE_AUDIO_INFO = 0x043B0102


def _sink(name, description, state="IDLE", kind=None, volume=50, muted=False):
    props = {
        "media.class": "Audio/Sink",
        "node.name": name,
        "node.description": description,
    }
    if kind == "speaker":
        props["api.alsa.path"] = "hw:0,1"
    if kind == "hdmi":
        props["api.alsa.path"] = "hw:0,22"
    if kind == "usb":
        props["device.bus"] = "usb"
    return {
        "index": abs(hash(name)) % 10000,
        "name": name,
        "description": description,
        "state": state,
        "mute": muted,
        "volume": {
            "front-left": {"value": int(655.36 * volume)},
            "front-right": {"value": int(655.36 * volume)},
        },
        "properties": props,
    }


def speaker_sink():
    return _sink(ao.SPEAKER_SINK, "S10+ speaker (RDMA1, 48 kHz)", "RUNNING", "speaker")


def hdmi_sink():
    return _sink(ao.HDMI_SINK, "ALSA Sink on hw:0,22", "IDLE", "hdmi")


def bt_sink(name="bluez_output.AA_BB_CC_DD_EE_FF.1"):
    return _sink(name, "Bluetooth headphones", "IDLE")


def usb_sink(name="alsa_output.usb-Generic_USB_Audio-00.HiFi__Speaker__sink"):
    return _sink(name, "USB-C DAC", "IDLE", "usb")


def hdmi_available(value=LIVE_AUDIO_INFO, display="Philips TV"):
    info = ao.parse_dp_audio_info(value, True, True)
    return {
        "available": info["available"],
        "dp_link": True,
        "secdp": "1",
        "extcon": "DP=1",
        "pcm": {"card": 0, "device": 22, "hw_path": "hw:0,22",
                "line": "00-22: DP Audio snd-soc-dummy-dai-22 :  : playback 1"},
        "pcm_present": True,
        "ch_hdmi_audio": value,
        "ch_hdmi_audio_hex": "0x%08x" % (value & 0xffffffff),
        "audio_info": info,
        "display_name": display,
        "sink_name": ao.HDMI_SINK,
        "blockers": [] if info["available"] else [info.get("reason")],
        "blocker": None if info["available"] else info.get("reason"),
    }


def hdmi_unavailable(reason="DisplayPort link is not ready"):
    return {
        "available": False, "dp_link": False, "secdp": "0", "extcon": "DP=0",
        "pcm": {"card": 0, "device": 22, "hw_path": "hw:0,22", "line": "DP Audio"},
        "pcm_present": True, "ch_hdmi_audio": -1,
        "ch_hdmi_audio_hex": "0xffffffff",
        "audio_info": ao.parse_dp_audio_info(-1, False, True),
        "display_name": None, "sink_name": ao.HDMI_SINK,
        "blockers": [reason], "blocker": reason,
    }


class FakeBackend:
    def __init__(self, sinks=None, default=ao.SPEAKER_SINK):
        self.sinks = {s["name"]: dict(s) for s in
                      (sinks if sinks is not None else [speaker_sink()])}
        self.default = default
        self.available_flag = True
        self.load_calls = 0
        self.unload_calls = 0
        self.load_fail = False
        self.fail_defaults = set()
        self.sink_inputs = ["73"]
        self.moved = []
        self.last_error = None

    def available(self):
        return self.available_flag

    def list_sinks(self):
        return [dict(s) for s in self.sinks.values()]

    def default_sink(self):
        return self.default if self.default in self.sinks else None

    def set_default(self, name):
        if name in self.fail_defaults or name not in self.sinks:
            self.last_error = "set_default refused %s" % name
            return False
        self.default = name
        self.last_error = None
        return True

    def set_volume(self, name, percent):
        sink = self.sinks.get(name)
        if sink is None:
            return False
        sink["volume"] = {
            "front-left": {"value": int(655.36 * percent)},
            "front-right": {"value": int(655.36 * percent)},
        }
        return True

    def set_muted(self, name, muted):
        sink = self.sinks.get(name)
        if sink is None:
            return False
        sink["mute"] = bool(muted)
        return True

    def list_sink_inputs(self):
        return list(self.sink_inputs)

    def move_sink_input(self, index, target):
        if target not in self.sinks:
            return False
        self.moved.append((str(index), target))
        return True

    def load_hdmi(self, hw_path, sink_name=ao.HDMI_SINK):
        self.load_calls += 1
        if self.load_fail or not self.available_flag:
            return False, None, "load refused"
        self.sinks[sink_name] = hdmi_sink()
        return True, 900 + self.load_calls, None

    def unload_hdmi(self, sink_name=ao.HDMI_SINK):
        self.unload_calls += 1
        self.sinks.pop(sink_name, None)
        if self.default == sink_name:
            self.default = ao.SPEAKER_SINK if ao.SPEAKER_SINK in self.sinks else None
        return True, None


def manager(tmp_path, backend, hdmi, *, policy=None):
    p = tmp_path / "output-policy.json"
    if policy is not None:
        p.write_text(json.dumps(policy), encoding="utf-8")
    return ao.AudioOutputManager(
        root=str(tmp_path), policy_path=str(p),
        state_path=str(tmp_path / "audio-outputs.json"),
        backend=backend, hdmi_reader=lambda: hdmi,
    )


def test_live_audio_info_word_is_decoded_as_a_real_endpoint():
    info = ao.parse_dp_audio_info(LIVE_AUDIO_INFO, True, True)
    assert info["valid"] is True
    assert info["available"] is True
    assert info["channels"] == 2
    assert info["channel_mask"] == 0x02
    assert info["sample_rate_flags"] != 0
    assert info["is_dp"] is True


def test_zero_and_minus_one_audio_info_are_unavailable():
    for value in (-1, 0, 1, 0xFFFFFFFF, 0x04000000):
        info = ao.parse_dp_audio_info(value, True, True)
        assert info["available"] is False, value


def test_pcm_parser_uses_runtime_card_and_device_not_a_hardcoded_path():
    pcm = ao.parse_dp_pcm(
        "00-01: RDMA1 (*) :  : playback 1\n"
        "00-22: DP Audio snd-soc-dummy-dai-22 :  : playback 1\n")
    assert pcm == {"card": 0, "device": 22, "hw_path": "hw:0,22",
                   "line": "00-22: DP Audio snd-soc-dummy-dai-22 :  : playback 1"}


def test_automatic_speaker_only(tmp_path):
    backend = FakeBackend()
    mgr = manager(tmp_path, backend, hdmi_unavailable())
    status = mgr.reconcile()
    assert status["backend_available"] is True
    assert status["current"]["kind"] == "speaker"
    assert [e["kind"] for e in status["endpoints"]] == ["speaker"]
    assert status["hdmi"]["available"] is False
    assert status["endpoint_state"] == "ACTIVE"


def test_boot_with_hdmi_already_attached_routes_hdmi(tmp_path):
    backend = FakeBackend()
    mgr = manager(tmp_path, backend, hdmi_available())
    status = mgr.reconcile()
    assert backend.load_calls == 1
    assert status["current"]["kind"] == "hdmi"
    assert status["current"]["stable_id"] == ao.HDMI_ID
    assert status["endpoint_state"] == "ACTIVE"
    assert status["hdmi"]["state"] == "ACTIVE"
    assert backend.default == ao.HDMI_SINK
    assert backend.moved == [("73", ao.HDMI_SINK)]
    assert "automatic" in status["last_decision"]["reason_code"]


def test_display_connected_without_hdmi_audio_is_not_offered(tmp_path):
    backend = FakeBackend()
    hdmi = hdmi_unavailable("EDID audio block advertises zero LPCM channels")
    mgr = manager(tmp_path, backend, hdmi)
    status = mgr.reconcile()
    assert status["current"]["kind"] == "speaker"
    assert all(e["kind"] != "hdmi" for e in status["endpoints"])
    assert "EDID audio" in status["hdmi"]["blocker"]


def test_delayed_hdmi_enumeration_then_automatic_route(tmp_path):
    backend = FakeBackend()
    state = {"hdmi": hdmi_unavailable()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    assert mgr.reconcile()["current"]["kind"] == "speaker"
    state["hdmi"] = hdmi_available(display="Delayed TV")
    status = mgr.reconcile()
    assert status["current"]["kind"] == "hdmi"
    assert backend.load_calls == 1


def test_hdmi_unplug_falls_back_and_removes_dynamic_sink(tmp_path):
    backend = FakeBackend()
    state = {"hdmi": hdmi_available()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    assert mgr.reconcile()["current"]["kind"] == "hdmi"
    state["hdmi"] = hdmi_unavailable("DisplayPort link is not ready")
    status = mgr.reconcile()
    assert status["current"]["kind"] == "speaker"
    assert ao.HDMI_SINK not in backend.sinks
    assert backend.unload_calls == 1


def test_hdmi_reconnect_restores_automatic_route(tmp_path):
    backend = FakeBackend()
    state = {"hdmi": hdmi_available()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    mgr.reconcile()
    state["hdmi"] = hdmi_unavailable()
    assert mgr.reconcile()["current"]["kind"] == "speaker"
    state["hdmi"] = hdmi_available()
    status = mgr.reconcile()
    assert status["current"]["kind"] == "hdmi"


def test_manual_speaker_is_never_overridden_by_hdmi_hotplug(tmp_path):
    backend = FakeBackend()
    state = {"hdmi": hdmi_unavailable()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    mgr.reconcile()
    assert mgr.select_output(ao.SPEAKER_ID)["current"]["kind"] == "speaker"
    state["hdmi"] = hdmi_available()
    status = mgr.reconcile()
    assert status["mode"] == "manual"
    assert status["current"]["kind"] == "speaker"
    assert status["preferred_id"] == ao.SPEAKER_ID


def test_manual_bluetooth_is_never_overridden_by_hdmi_hotplug(tmp_path):
    backend = FakeBackend(sinks=[speaker_sink(), bt_sink()])
    state = {"hdmi": hdmi_unavailable()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    mgr.reconcile()
    bt = next(e for e in mgr.status()["endpoints"] if e["kind"] == "bluetooth")
    mgr.select_output(bt["stable_id"])
    state["hdmi"] = hdmi_available()
    status = mgr.reconcile()
    assert status["current"]["kind"] == "bluetooth"
    assert status["current"]["stable_id"] == bt["stable_id"]


def test_manual_usb_is_never_overridden_by_hdmi_hotplug(tmp_path):
    backend = FakeBackend(sinks=[speaker_sink(), usb_sink()])
    state = {"hdmi": hdmi_unavailable()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    mgr.reconcile()
    usb = next(e for e in mgr.status()["endpoints"] if e["kind"] == "usb")
    mgr.select_output(usb["stable_id"])
    state["hdmi"] = hdmi_available()
    status = mgr.reconcile()
    assert status["current"]["kind"] == "usb"
    assert status["current"]["stable_id"] == usb["stable_id"]


def test_selected_device_disappears_then_returns_and_is_restored(tmp_path):
    bt = bt_sink()
    backend = FakeBackend(sinks=[speaker_sink(), bt])
    state = {"hdmi": hdmi_unavailable()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    mgr.reconcile()
    bt_id = next(e["stable_id"] for e in mgr.status()["endpoints"]
                if e["kind"] == "bluetooth")
    mgr.select_output(bt_id)
    backend.sinks.pop(bt["name"])
    status = mgr.reconcile()
    assert status["current"]["kind"] == "speaker"
    assert status["preferred_id"] == bt_id
    assert status["preferred_available"] is False
    assert status["fallback_active"] is True
    backend.sinks[bt["name"]] = bt
    status = mgr.reconcile()
    assert status["current"]["kind"] == "bluetooth"
    assert status["preferred_available"] is True


def test_return_to_automatic_reevaluates_connected_hdmi(tmp_path):
    backend = FakeBackend()
    state = {"hdmi": hdmi_available()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    mgr.reconcile()
    mgr.select_output(ao.SPEAKER_ID)
    assert mgr.status()["current"]["kind"] == "speaker"
    status = mgr.set_automatic()
    assert status["mode"] == "automatic"
    assert status["current"]["kind"] == "hdmi"


def test_audio_server_restart_is_recovered_without_leaving_a_ghost_route(tmp_path):
    backend = FakeBackend()
    state = {"hdmi": hdmi_available()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    assert mgr.reconcile()["current"]["kind"] == "hdmi"
    backend.available_flag = False
    status = mgr.reconcile()
    assert status["backend_available"] is False
    assert status["endpoints"] == []
    backend.available_flag = True
    status = mgr.reconcile()
    assert status["backend_available"] is True
    assert status["current"]["kind"] == "hdmi"


def test_rapid_hotplug_does_not_create_duplicate_hdmi_sinks(tmp_path):
    backend = FakeBackend()
    state = {"hdmi": hdmi_available()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    for _ in range(3):
        state["hdmi"] = hdmi_available()
        mgr.reconcile()
        state["hdmi"] = hdmi_unavailable()
        mgr.reconcile()
    state["hdmi"] = hdmi_available()
    status = mgr.reconcile()
    assert status["current"]["kind"] == "hdmi"
    assert list(backend.sinks).count(ao.HDMI_SINK) == 1
    assert backend.load_calls >= 1


def test_route_switch_failure_keeps_previous_working_output(tmp_path):
    backend = FakeBackend()
    backend.fail_defaults.add(ao.HDMI_SINK)
    mgr = manager(tmp_path, backend, hdmi_available())
    status = mgr.reconcile()
    assert status["current"]["kind"] == "speaker"
    assert backend.default == ao.SPEAKER_SINK
    assert status["last_route"]["success"] is False
    assert status["last_route"]["error"] == "ROUTE_FAILED"


def test_hdmi_sink_activation_failure_reports_fallback_not_fake_hdmi(tmp_path):
    backend = FakeBackend()
    backend.load_fail = True
    mgr = manager(tmp_path, backend, hdmi_available())
    status = mgr.reconcile()
    assert status["current"]["kind"] == "speaker"
    assert all(e["kind"] != "hdmi" for e in status["endpoints"])
    assert "HDMI sink activation failed" in (status["last_error"] or "")


def test_no_speaker_falls_back_to_last_valid_non_hdmi(tmp_path):
    backend = FakeBackend(sinks=[bt_sink()], default=bt_sink()["name"])
    mgr = manager(tmp_path, backend, hdmi_unavailable())
    status = mgr.reconcile()
    assert status["current"]["kind"] == "bluetooth"


def test_no_output_is_reported_without_changing_a_nonexistent_sink(tmp_path):
    backend = FakeBackend(sinks=[], default=None)
    mgr = manager(tmp_path, backend, hdmi_unavailable())
    status = mgr.reconcile()
    assert status["current"] is None
    assert status["endpoints"] == []
    assert status["last_route"]["error"] == "NO_OUTPUT"


def test_manual_and_fallback_identity_persist_by_stable_id(tmp_path):
    backend = FakeBackend()
    state = {"hdmi": hdmi_available()}
    mgr = manager(tmp_path, backend, state["hdmi"])
    mgr.hdmi_reader = lambda: state["hdmi"]
    mgr.reconcile()
    mgr.select_output(ao.SPEAKER_ID)
    policy = json.loads((tmp_path / "output-policy.json").read_text())
    assert policy["mode"] == "manual"
    assert policy["preferred_id"] == ao.SPEAKER_ID
    assert policy["preferred_name"] == "Phone speaker"
    assert "card" not in json.dumps(policy).lower()
    backend2 = FakeBackend()
    mgr2 = manager(tmp_path, backend2, hdmi_available())
    status = mgr2.reconcile()
    assert status["mode"] == "manual"
    assert status["current"]["kind"] == "speaker"


def test_malformed_policy_falls_back_to_automatic(tmp_path):
    backend = FakeBackend()
    mgr = manager(tmp_path, backend, hdmi_available(),
                  policy={"mode": "manual", "preferred_id": "bad id with spaces"})
    assert mgr.prefs.mode == "automatic"
    status = mgr.reconcile()
    assert status["current"]["kind"] == "hdmi"


def test_volume_and_mute_follow_the_current_sink(tmp_path):
    backend = FakeBackend()
    mgr = manager(tmp_path, backend, hdmi_unavailable())
    mgr.reconcile()
    assert mgr.set_volume(37)["volume_percent"] == 37
    assert mgr.status()["volume_percent"] == 37
    assert mgr.set_muted(True)["muted"] is True
    assert mgr.status()["muted"] is True


def test_soundd_routes_new_verbs_to_one_audio_manager():
    soundd = (ROOT / "services/nuxel-sound/nuxel-soundd.py").read_text()
    for needle in ("AudioOutputManager(", "set-routing", "select-output",
                   "set-volume", "set-muted", "test-output",
                   "MANAGER.audio.start()"):
        assert needle in soundd


def test_bridge_forwards_output_policy_and_never_mocks_it():
    api = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    for needle in ("'cmd': 'outputs'", "set-routing", "select-output",
                   "set-volume", "set-muted", "test-output"):
        assert needle in api
    js = (ROOT / "pwa/nuxel-common/bridge.js").read_text()
    for key in ("sound.outputs", "sound.set-routing", "sound.select-output",
                "sound.set-volume", "sound.set-muted", "sound.test-output"):
        assert key in js


def test_settings_sound_exposes_required_live_controls():
    html = (ROOT / "pwa/nuxel-apps/settings/index.html").read_text()
    js = (ROOT / "pwa/nuxel-apps/settings/sound-settings.js").read_text()
    for ident in ("sound-output-devices", "sound-output-auto",
                  "sound-output-volume", "sound-output-mute",
                  "sound-output-test", "sound-output-state"):
        assert 'id="%s"' % ident in html
    for verb in ("outputs", "set-routing", "select-output",
                 "set-volume", "set-muted", "test-output"):
        assert "call('%s'" % verb in js
    assert "setInterval" in js and "2000" in js
    assert "Manual override" in js and "fallback" in js.lower()
    assert "audio-output-hdmi" not in html
    assert "audio-output-speaker" not in html


def test_cli_exposes_safe_output_commands():
    cli = (ROOT / "services/nuxel-sound/nuxel-soundctl").read_text()
    for command in ("outputs", "automatic", "select", "volume", "mute",
                    "test", "diagnostics"):
        assert '"%s"' % command in cli or "'%s'" % command in cli


def test_display_model_uses_the_shared_non_boolean_audio_info_parser():
    text = (ROOT / "services/nuxel-display/lib/nuxel_display.py").read_text()
    assert "nuxel_audio_outputs import parse_dp_audio_info" in text
    assert "ch_hdmi_audio != 1" not in text
