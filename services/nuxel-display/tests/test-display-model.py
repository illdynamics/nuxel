#!/usr/bin/env python3
"""Offline tests for the Nuxel external-display model.

No hardware: fixture roots emulate the S10+ sysfs/procfs interfaces measured on
the live device.  The tests prove the model distinguishes each real failure
stage and never invents a monitor or a mode.
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(HERE, "..", "lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import nuxel_display as nd  # noqa: E402


def write(root, rel, text):
    path = os.path.join(root, rel.lstrip("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    return path


def link(root, rel, target):
    path = os.path.join(root, rel.lstrip("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.lexists(path):
        os.unlink(path)
    os.symlink(target, path)


def fixture(partner=True, pd=False, dp=False, fb=True, audio=False, monitor=False):
    root = tempfile.mkdtemp(prefix="nx-display-model-")
    write(root, "sys/class/typec/port0/data_role", "host [device]\n")
    write(root, "sys/class/typec/port0/power_role", "source [sink]\n")
    write(root, "sys/class/typec/port0/power_operation_mode", "default\n")
    if partner:
        write(root, "sys/class/typec/port0-partner/supports_usb_power_delivery",
              "yes\n" if pd else "no\n")
        write(root, "sys/class/typec/port0-partner/accessory_mode", "none\n")
    write(root, "sys/class/extcon/extcon0/name", "130b0000.displayport\n")
    write(root, "sys/class/extcon/extcon0/state", "DP=%d\n" % (1 if dp else 0))
    write(root, "sys/class/switch/secdp/state", "1\n" if dp else "0\n")
    write(root, "sys/class/switch/secdp_msg/state", "0\n")
    # Live S10+ value on 2026-11-09: 0x043b0102 (2ch LPCM, 48 kHz, DP).
    # The vendor switch is an EDID-derived bitmask, never a boolean.
    write(root, "sys/class/switch/ch_hdmi_audio/state",
          "0x043b0102\n" if audio else "-1\n")
    write(root, "sys/class/sec/ccic/state", "3\n")
    write(root, "sys/class/sec/ccic/usbpd_ids",
          "18d1:4ee7\n" if pd else "0000:0000\n")
    write(root, "sys/class/sec/ccic/usbpd_type", "200\n" if pd else "0\n")
    write(root, "sys/class/sec/ccic/rid", "7\n")
    write(root, "sys/class/sec/ccic/sbu_adc", "10 6\n")
    write(root, "sys/class/sec/ccic/cc_pin_status", "2\n")
    write(root, "sys/class/sec/ccic/cur_version", "1A.00\n")
    write(root, "sys/class/sec/ccic/src_version", "1A.00\n")
    write(root, "sys/class/dp_sec/dex", "0\n")
    write(root, "sys/class/dp_sec/dp_drm", "DRM state 0\n")
    write(root, "sys/class/dp_sec/monitor_info",
          "BNQ,0x7f54,0x5445\n" if monitor else ",0x0,0x0\n")
    write(root, "sys/class/dp_sec/forced_resolution",
          " 0 : V640X480P60\n 9 : V1920X1080P60\n")
    write(root, "sys/class/dp_sec/audio_test", "channel: 0\n")
    write(root, "sys/class/dp_sec/unit_test", "1\n")
    write(root, "sys/class/dp_sec/dp_test", "0: HPD test\n")
    write(root, "proc/asound/pcm",
          "00-22: DP Audio snd-soc-dummy-dai-22 :  : playback 1\n")
    if fb:
        link(root, "sys/class/graphics/fb1/device",
             "../../devices/platform/19050000.decon_t")
        write(root, "sys/class/graphics/fb1/virtual_size", "640,960\n")
        write(root, "sys/class/graphics/fb1/stride", "2560\n")
        write(root, "sys/class/graphics/fb1/bits_per_pixel", "32\n")
        write(root, "sys/class/graphics/fb1/rotate", "0\n")
        write(root, "sys/class/graphics/fb1/blank", "0\n")
        write(root, "sys/class/graphics/fb1/state", "0\n")
        write(root, "sys/class/graphics/fb1/mode", "")
        write(root, "sys/class/graphics/fb1/modes", "U:640x480p-0\n")
    # fb0 is always present on the real device; include it so the test covers
    # the "internal screen preserved" assertion.
    link(root, "sys/class/graphics/fb0/device",
         "../../devices/platform/19030000.decon_f")
    write(root, "sys/class/graphics/fb0/modes", "U:1440x3040p-0\n")
    return root


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        raise AssertionError(msg)


def test_parse_fb_modes():
    modes = nd.parse_fb_modes("U:1920x1080p-60\nU:1280x720p-0\n")
    check(len(modes) == 2, "two fb modes parsed")
    check(modes[0]["width"] == 1920 and modes[0]["height"] == 1080,
          "1920x1080 parsed")
    check(modes[0]["refresh"] == 60, "refresh parsed")


def test_no_partner():
    st = nd.read_snapshot(fixture(partner=False))
    check(st["state"] == nd.DISCONNECTED, "no partner -> DISCONNECTED")
    check(st["mirror_supported"] is False, "no mirror without a partner")
    check("Type-C partner" in (st["blocker"] or ""), "blocker names the missing partner")


def test_partner_without_pd_is_the_live_adapter_state():
    st = nd.read_snapshot(fixture(partner=True, pd=False, fb=True))
    check(st["state"] == nd.PARTNER_NO_PD, "partner without PD -> PARTNER_NO_PD")
    check("USB-PD identity" in (st["blocker"] or ""),
          "blocker explains the missing USB-PD identity")
    check(st["mirror_supported"] is False, "mirror unavailable before VDM/DP")
    check(st["display_name"] is None, "monitor_info is not trusted without a DP link")


def test_pd_without_dp():
    st = nd.read_snapshot(fixture(partner=True, pd=True, dp=False, fb=True))
    check(st["state"] == nd.PD_NO_DP, "PD without DP -> PD_NO_DP")
    check(st["mirror_supported"] is False, "mirror unavailable without DP")


def test_dp_ready_mirror():
    st = nd.read_snapshot(fixture(partner=True, pd=True, dp=True, fb=True,
                                  audio=True, monitor=True))
    check(st["state"] == nd.DP_LINK_READY, "DP link + fb1 -> DP_LINK_READY")
    check(st["mirror_supported"] is True, "mirror offered when DP+fb1 are ready")
    check(st["external_fb_present"] is True, "external fb1 reported")
    check(st["external_fb"]["device"] == "19050000.decon_t",
          "fb1 is tied to decon_t")
    check(st["external_modes"][0]["width"] == 640, "fb1 mode parsed")
    check(st["display_name"] == "BenQ 0x7f54", "live monitor identity reported")
    check(st["audio"]["available"] is True,
          "DP audio available from the EDID audio-info bitmask")
    check(st["audio"]["dp_audio_pcm"] is True, "DP Audio PCM detected")
    check(st["blocker"] is None, "ready state has no blocker")


def test_dp_without_fb():
    st = nd.read_snapshot(fixture(partner=True, pd=True, dp=True, fb=False))
    check(st["state"] == nd.DP_NO_FB, "DP without decon_t fb -> DP_NO_FB")
    check(st["mirror_supported"] is False, "no mirror without an external fb")


def test_choose_outputs():
    outs = [
        {"name": "HEADLESS-1", "enabled": True, "position": "0,0"},
        {"name": "HEADLESS-2", "enabled": True, "position": "720,0"},
    ]
    chosen = nd.choose_outputs(outs)
    check(chosen["primary"]["name"] == "HEADLESS-1", "primary is the phone output")
    check(chosen["external"]["name"] == "HEADLESS-2", "second output is external")
    chosen = nd.choose_outputs(outs[:1])
    check(chosen["external"] is None, "no external output when only one exists")


def test_state_machine_reconnect_generations():
    sm = nd.DisplayStateMachine()
    ready = {"state": nd.DP_LINK_READY}
    check(sm.update({"state": nd.DISCONNECTED}) == [], "initial disconnected is quiet")
    ev = sm.update(ready)
    check(len(ev) == 1 and ev[0]["event"] == "connected", "first ready -> connected")
    gen1 = sm.generation
    check(sm.should_notify() is True, "new generation should notify")
    sm.mark_notified()
    check(sm.should_notify() is False, "repeat ready does not re-notify")
    check(sm.update(ready) == [], "duplicate ready polls produce no events")
    ev = sm.update({"state": nd.PARTNER_NO_PD})
    check(ev and ev[0]["event"] == "disconnected", "loss of DP -> disconnected")
    check(sm.mode == nd.MODE_OFF, "disconnect resets mode to off")
    ev = sm.update(ready)
    check(ev and ev[0]["generation"] == gen1 + 1, "reconnect creates a new generation")
    check(sm.should_notify() is True, "reconnect requires a new notification")


def test_notification_payload():
    st = nd.read_snapshot(fixture(partner=True, pd=True, dp=True, fb=True,
                                  audio=True, monitor=True))
    st["desktop_supported"] = False
    st["desktop_supported"] = True
    payload = nd.notification_payload(st, 7, suggested_mode=nd.MODE_MIRROR)
    check(payload["summary"] == "External display connected", "connection summary")
    check("Mirror portrait" in payload["actions"], "portrait action present")
    check("Mirror landscape" in payload["actions"], "landscape action present")
    check("Fullscreen" in payload["actions"], "fullscreen action present")
    check("Separate desktop" in payload["actions"], "desktop action present")
    st_no_desktop = dict(st); st_no_desktop["desktop_supported"] = False
    payload_no_desktop = nd.notification_payload(st_no_desktop, 8)
    check("Separate desktop" not in payload_no_desktop["actions"],
          "unavailable desktop action is not offered")
    check(payload["hints"]["nuxel.display.generation"] == 7, "generation in hints")
    check("BenQ" in payload["body"], "detected display identity used in body")
    err = nd.notification_payload(st, 7, error="DP link is not ready")
    check(err["summary"] == "External display mode failed", "error notification summary")
    check("DP link is not ready" in err["body"], "error detail preserved")


def test_mode_errors():
    st = nd.read_snapshot(fixture(partner=True, pd=False, fb=True))
    check(nd.mode_error(st, nd.MODE_MIRROR) is not None, "mirror refused before DP")
    st = nd.read_snapshot(fixture(partner=True, pd=True, dp=True, fb=True,
                                  monitor=True))
    st["desktop_supported"] = False
    check(nd.mode_error(st, nd.MODE_MIRROR) is None, "mirror allowed when DP ready")
    check(nd.mode_error(st, nd.MODE_DESKTOP) is not None,
          "desktop refused without a second output")
    st["desktop_supported"] = True
    check(nd.mode_error(st, nd.MODE_DESKTOP) is None, "desktop allowed with two outputs")


def main():
    print("nuxel-display model tests")
    test_parse_fb_modes()
    test_no_partner()
    test_partner_without_pd_is_the_live_adapter_state()
    test_pd_without_dp()
    test_dp_ready_mirror()
    test_dp_without_fb()
    test_choose_outputs()
    test_state_machine_reconnect_generations()
    test_notification_payload()
    test_mode_errors()
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
