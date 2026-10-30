"""PWNAGE-38000 follow-up regressions (2026-10-29, measured on the handset).

Two operator-visible defects were fixed and are pinned here:

1. **No audio.**  The S10+ static PipeWire sink and the ALSA default were pinned
   to 44.1 kHz.  On the live unit `hw:0,1` (RDMA1) only advances `hw_ptr` at
   48 kHz; at 44.1 kHz `aplay` returns EIO with `hw_ptr` stuck at 0, so every
   PipeWire/GStreamer playback silently produced no sound.  The sink, the graph
   clock, and the docs must all agree on 48 kHz.

2. **The old Nuxel splash for ~2 s.**  The initramfs did not carry
   `opt/nuxel/nuxel-firstlight.rawspl`, so `nuxel-fb-phone` took its A16
   diagnostic fallback and painted the obsolete splash before the MP4 player
   committed animation frame 0.  The initramfs must never paint that legacy
   frame when the asset is absent, and the repack tool must ship the asset.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── 1. audio rate ───────────────────────────────────────────────────────────
def test_static_pipewire_sink_uses_48k():
    conf = _read("configs/s10plus/pipewire/50-nuxel-s10-alsa.conf")
    assert re.search(r"^\s*audio\.rate\s*=\s*48000\s*$", conf, re.M), conf
    assert "44100" not in conf
    assert "48 kHz" in conf


def test_pipewire_graph_clock_uses_48k():
    conf = _read("services/nuxel-s10/pipewire/99-nuxel-s10.conf")
    assert re.search(r"^\s*default\.clock\.rate\s*=\s*48000\s*$", conf, re.M), conf
    assert "44100" not in conf


def test_alsa_default_has_no_44100_pin():
    for rel in ("services/nuxel-s10/alsa/99-nuxel-s10-default.conf",
                "configs/s10plus/alsa/asound.conf"):
        conf = _read(rel)
        # The plug layer must not pin the hardware rate; it resamples 44.1 kHz
        # consumers onto the 48 kHz PCM.
        assert "44100" not in re.sub(r"#.*", "", conf), rel
        assert "device 1" in conf, rel


def test_audio_policy_records_measured_48k_route():
    import json
    policy = json.loads(_read("configs/nuxel/audio/audio.json"))
    route = policy["card_selection"]["measured_working_route"]
    assert "48000" in route
    assert "hw:0,1" in route


def test_route_script_does_not_claim_44k_working():
    route = _read("services/nuxel-s10/bin/nuxel-audio-route.sh")
    assert "48 kHz" in route
    assert "RDMA1" in route


# ── 2. first light must never paint the legacy frame ────────────────────────
def test_init_does_not_paint_legacy_frame_when_asset_missing():
    init = _read("boot/initramfs/init.sh")
    assert "FIRSTLIGHT_ASSET_MISSING_NO_LEGACY_PAINT" in init
    # the old unconditional invocation must be gone
    assert "FIRSTLIGHT asset ABSENT from this initramfs -> A16 diagnostic frame" not in init
    # the painter call must be inside the asset-present branch
    present = init.split("if [ -f /opt/nuxel/nuxel-firstlight.rawspl ]; then", 1)
    assert len(present) == 2, "asset-present guard missing"
    guarded = present[1].split("else", 1)[0]
    assert "--firstlight=/opt/nuxel/nuxel-firstlight.rawspl" in guarded
    absent = present[1].split("else", 1)[1].split("fi", 1)[0]
    assert "--firstlight=" not in absent


def test_repack_tool_ships_the_firstlight_asset():
    tool = _read("tools/s10plus/a27/repack-splashfix.sh")
    assert "opt/nuxel/nuxel-firstlight.rawspl" in tool
    assert "make-firstlight-asset.py" in tool
    # it must keep the partition size exactly, and preserve the kernel
    assert "ramdisk_size" in tool
    assert "partition" in tool
