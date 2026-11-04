import argparse
import pathlib
import subprocess
import sys

import pytest

from conftest import load_script

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_default_is_explicit_software(play):
    text = (ROOT / "tools/s10plus/a61/nuxel-mfc-play").read_text()
    assert '"--hwdec=no"' in text
    assert "decoder=software" in text


def test_hardware_refuses_without_real_decode_state(play, tmp_path, capsys):
    args = argparse.Namespace(width=1920, height=1080, input="/tmp/x.h264",
                              receipt=str(tmp_path / "r.json"), max_frames=0,
                              timeout=10)
    rc = play.hardware(args, [], {"state": "AVAILABLE_PROBE_ONLY", "reason": "no proof",
                                  "decoder_node": "/dev/video6"})
    assert rc == 1
    err = capsys.readouterr().err
    assert "REFUSED" in err
    assert "AVAILABLE_PROBE_ONLY" in err


def test_show_policy_never_claims_hardware(play, monkeypatch, capsys):
    monkeypatch.setattr(play, "run_status", lambda: {"state": "BLOCKED_FIRMWARE_MISSING",
                                                      "reason": "missing",
                                                      "decoder_node": None})
    rc = play.main(["--show-policy"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"policy": "software"' in out
    assert '"software_fallback": true' in out
