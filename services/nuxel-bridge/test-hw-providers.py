#!/usr/bin/env python3
"""Offline tests for the privileged audio/display/bluetooth hardware providers.

No real hardware, no shell-out: the test injects fixture roots and canned
amixer/systemctl results, and proves the providers report missing hardware,
discover controls from observed names only, clamp volume to the low-volume cap,
and never invent a monitor or a radio.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
MODULE = os.path.join(SRC, "hw_providers.py")
spec = importlib.util.spec_from_file_location("hw_providers", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILURES = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def write(root, rel, text):
    path = os.path.join(root, rel.lstrip("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    return path


def test_audio_inventory():
    root = tempfile.mkdtemp(prefix="nx-audio-")
    write(root, "proc/asound/cards",
          " 0 [beyondmadera   ]: beyond-madera - beyond-madera\n"
          "                      beyond-madera\n")
    write(root, "proc/asound/pcm",
          "00-00: RDMA0 (*) :  : playback 1\n"
          "00-12: WDMA0 (*) :  : capture 1\n")

    ap = mod.AudioProvider(root=root, card=0)
    # No amixer on the offline host: _run_amixer returns (None, err).
    ap._run_amixer = lambda *a: (None, "no amixer")
    st = ap.get_status()
    check(st["success"] is True, "audio status reports success for inventory")
    check(st["state"] == "present", "a real card in /proc/asound is present")
    check(len(st["cards"]) == 1, "one ALSA card parsed")
    check(st["cards"][0]["name"].startswith("beyond-madera"), "card name parsed from /proc/asound")
    check(st["playback_devices"][0]["id"] == "RDMA0", "playback PCM parsed")
    check(st["capture_devices"][0]["id"] == "WDMA0", "capture PCM parsed")
    check(st["volume_supported"] is False, "no volume control is invented without amixer")


def test_audio_volume_discovery_and_clamp():
    root = tempfile.mkdtemp(prefix="nx-audio-")
    write(root, "proc/asound/cards", " 0 [beyondmadera   ]: beyond-madera - beyond-madera\n")
    write(root, "proc/asound/pcm", "00-00: RDMA0 (*) :  : playback 1\n")
    ap = mod.AudioProvider(root=root, card=0, volume_cap=25)

    def fake_amixer(*args):
        # args[0] is always "sget" or "sset" now; args[1] is the control name.
        control = args[1] if len(args) > 1 else None
        if args and args[0] == "sget":
            if control == "HPOUT1 Digital":
                return ("Simple mixer control 'HPOUT1 Digital',0\n"
                        "  Capabilities: pvolume pswitch\n"
                        "  Playback channels: Front Left - Front Right\n"
                        "  Front Left: Playback 60 [60%]\n", None)
            return ("amixer: Unable to find simple control '%s',0\n" % control, None)
        if args and args[0] == "sset":
            return "", None
        return None, "unexpected"
    ap._run_amixer = fake_amixer

    st = ap.get_status()
    check(st["volume_control"] == "HPOUT1 Digital", "discovers the observed playback control")
    check(st["volume_supported"] is True, "volume is supported when a real control exists")
    check(st["volume_percent"] == 60, "current volume percent read from mixer")

    r = ap.set_volume(100)
    check(r["requested_percent"] == 25, "volume request clamped to the low-volume cap")
    check(r["control"] == "HPOUT1 Digital", "set targets the discovered control")


def test_audio_unmute_refused():
    root = tempfile.mkdtemp(prefix="nx-audio-")
    write(root, "proc/asound/cards", " 0 [beyondmadera   ]: beyond-madera - beyond-madera\n")
    write(root, "proc/asound/pcm", "00-00: RDMA0 (*) :  : playback 1\n")
    ap = mod.AudioProvider(root=root, card=0, volume_cap=25)
    r = ap.set_muted(False)
    check(r["success"] is False, "unmute is refused rather than wedging the codec")
    check(r.get("error_code") == "UNMUTE_UNSUPPORTED", "unmute refusal is typed")


def test_audio_missing_hardware():
    root = tempfile.mkdtemp(prefix="nx-audio-")
    ap = mod.AudioProvider(root=root, card=0)
    ap._run_amixer = lambda *a: (None, "no amixer")
    st = ap.get_status()
    check(st["state"] == "unavailable", "no card -> unavailable state")
    check(st["cards"] == [], "no fabricated card")
    check(st["volume_supported"] is False, "no fabricated volume control")


def test_display_no_drm_blocker():
    root = tempfile.mkdtemp(prefix="nx-display-")
    # No /sys/class/drm -> the image renders via framebuffer.
    write(root, "sys/class/typec/port0/data_role", "host [device]\n")
    write(root, "sys/class/typec/port0/power_role", "source [sink]\n")
    write(root, "sys/class/extcon/extcon0/name", "DisplayPort\n")
    write(root, "sys/class/extcon/extcon0/state", "USB_DP=0\n")
    dp = mod.DisplayProvider(root=root)
    st = dp.get_status()
    check(st["drm_present"] is False, "no DRM entries -> not present")
    check(st["mirror_supported"] is False, "Mirror is not offered without DRM")
    check(st["desktop_supported"] is False, "Desktop is not offered without DRM")
    check("CONFIG_DRM" in (st["blocker"] or ""), "blocker names the missing kernel DRM path")
    check(len(st["type_c_ports"]) == 1, "Type-C port evidence is reported")


def test_bluetooth_power_rfkill_and_service():
    root = tempfile.mkdtemp(prefix="nx-bt-")
    write(root, "sys/class/rfkill/rfkill0/type", "bluetooth\n")
    write(root, "sys/class/rfkill/rfkill0/soft", "1\n")

    calls = []
    real_run = mod.subprocess.run
    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()
    mod.subprocess.run = fake_run
    try:
        r = mod.bluetooth_set_power(True, root=root)
    finally:
        mod.subprocess.run = real_run

    check(r["success"] is True, "power bring-up succeeds when rfkill + systemctl work")
    with open(os.path.join(root, "sys/class/rfkill/rfkill0/soft")) as f:
        check(f.read().strip() == "0", "rfkill soft block is cleared on enable")
    check(any(c and c[0].endswith("systemctl") and c[1] == "start" for c in calls), "bluetooth.service is started")


def main():
    test_audio_inventory()
    test_audio_volume_discovery_and_clamp()
    test_audio_missing_hardware()
    test_audio_unmute_refused()
    test_display_no_drm_blocker()
    test_bluetooth_power_rfkill_and_service()
    print("\n" + ("ALL PASS" if not FAILURES else "%d FAILURES" % len(FAILURES)))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
