"""PWNAGE-40000 regressions: boot readiness, honest gate, and persistence.

These pin the defects measured on the handset on 2026-10-30:

  * `nuxel-boot-sound.service` failed at 09:35:45Z because ExecStartPre ran a
    ONE-SHOT `--check` 0.1 s after the ABOX reload, before the CS35L41 DSP1
    protection firmware had booted.  The gate must be able to wait, bounded.
  * The ABOX wrapper started the route *before* PipeWire existed, so the route
    deferred ("static PipeWire sink absent") and boot-sound raced it.
  * The route script rewrote DSP1 firmware/preload on every 5-minute retry,
    and slammed the volume to 0.25 over a user's quieter setting.
  * The static sink had to be verified at 48 kHz, not just "present".
  * `_ensure_default_sink()` accepts neither a non-48k sink nor a `null`
    default read-back.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


ROUTE = "services/nuxel-s10/bin/nuxel-audio-route.sh"
CUE_UNIT = "services/nuxel-session/systemd/nuxel-boot-sound.service"
ABOX_BOOT = "services/nuxel-s10/bin/nuxel-abox-firmware-reload-boot.sh"
HW = "services/nuxel-bridge/src/hw_providers.py"
DETECTOR = "tools/s10plus/a33/notes-works-detector.py"


# ── route gate ─────────────────────────────────────────────────────────────
def test_route_has_bounded_wait_mode():
    route = _read(ROUTE)
    assert "--wait)" in route
    assert "WAIT_SECONDS" in route
    assert "while :; do" in route
    # the wait loop is read-only: it must not apply mixer writes
    wait_block = route.split('if [ "$CHECK_ONLY" -eq 1 ]; then', 1)[1].split("\nfi\n", 1)[0]
    assert "cset" not in wait_block
    assert "wpctl set-volume" not in wait_block


def test_boot_cue_waits_instead_of_failing_on_first_sample():
    unit = _read(CUE_UNIT)
    assert "ExecStartPre=/usr/lib/nuxel/nuxel-audio-route.sh --wait 200" in unit
    # a one-shot check was the measured failure
    assert "ExecStartPre=/usr/lib/nuxel/nuxel-audio-route.sh --check\n" not in unit
    assert "TimeoutStartSec=240" in unit


def test_route_requires_rdma1_en_and_48k_sink():
    route = _read(ROUTE)
    assert "'ABOX RDMA1_EN' 1" in route
    assert "sink_rate_ok" in route
    assert "48000Hz" in route
    assert "pipewire_connectable" in route
    assert "PipeWire:Interface:Core" in route


def test_route_writes_are_idempotent_and_preserve_user_volume():
    route = _read(ROUTE)
    # set_ctl reads first
    block = route.split("set_ctl() {", 1)[1].split("\n}\n", 1)[0]
    assert 'got=$(read_ctl "$2")' in block
    assert "already set" in block
    # volume only lowered when above the cap
    assert "v + 0 > cap + 0.0001" in route
    assert "left unchanged" in route


def test_route_keeps_25_percent_ceiling():
    route = _read(ROUTE)
    assert 'VOLUME_CAP=${NUXEL_AUDIO_VOLUME_CAP:-0.25}' in route


# ── ABOX boot wrapper ──────────────────────────────────────────────────────
def test_abox_wrapper_starts_session_before_route_and_waits():
    script = _read(ABOX_BOOT)
    start = script.split("start_session() {", 1)[1].split("\n}\n", 1)[0]
    # session first, then wait for the PipeWire socket, then apply the route
    assert start.index("nuxel-wayland.service") < start.index("nuxel-audio-route.service")
    assert "pipewire-0" in start
    assert "systemctl start nuxel-audio-route.service" in start
    assert "systemctl --no-block start nuxel-audio-route.sh" not in start


# ── bridge ─────────────────────────────────────────────────────────────────
def test_ensure_default_sink_requires_48k_and_exact_readback():
    hw = _read(HW)
    assert 'if "48000Hz" not in sink_line:' in hw
    assert "return value == expected" in hw


def test_test_audio_checks_route_first():
    hw = _read(HW)
    assert "def _route_ready(" in hw
    block = hw.split("def test_audio(", 1)[1]
    assert block.index("self._route_ready()") < block.index("self._pipewire_play(")


def test_test_audio_never_claims_audibility():
    hw = _read(HW)
    assert '"audible": "unverified"' in hw


# ── Notes detector ─────────────────────────────────────────────────────────
def test_detector_discovers_the_session_atspi_bus_before_import():
    det = _read(DETECTOR)
    # Ignore prose/docstrings: only executable lines matter.
    code = [ln.strip() for ln in det.splitlines()
            if not ln.lstrip().startswith("#")]
    call = next(i for i, ln in enumerate(code) if ln == "_discover_atspi_bus()")
    imp = next(i for i, ln in enumerate(code) if ln == "import gi")
    # bus discovery must happen before gi/Atspi import, else libatspi is blind
    assert call < imp, "AT_SPI_BUS_ADDRESS must be set before libatspi loads"
    assert "AT_SPI_BUS_ADDRESS" in det


def test_detector_requires_focus_and_fresh_text():
    det = _read(DETECTOR)
    assert "title['focused'] and title['showing'] and title['editable']" in det
    assert "changed_away" in det
    assert "store_match(state, baseline_epoch)" in det


def test_detector_never_passes_on_player_exit_code():
    det = _read(DETECTOR)
    assert "pw-play" not in det
    assert "returncode" not in det


# ── 48 kHz drift (measured after the 2026-10-30 reboot) ────────────────────
def test_repo_pipewire_graph_clock_is_48k():
    conf = _read("services/nuxel-s10/pipewire/99-nuxel-s10.conf")
    active = "\n".join(ln for ln in conf.splitlines() if not ln.lstrip().startswith("#"))
    assert "default.clock.rate = 48000" in active
    # 44100 here silently resampled the RDMA1 stream even though the sink was 48k
    assert "44100" not in active


def test_pwnage36000_bundle_does_not_reinstall_44k():
    """The staged bundle rewrote the live graph file to 44100 at boot."""
    bundle = _read("services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh")
    src = _read("services/nuxel-s10/pipewire/99-nuxel-s10.conf")
    active = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    assert "44100" not in active
    assert "pipewire/99-nuxel-s10.conf" in bundle
