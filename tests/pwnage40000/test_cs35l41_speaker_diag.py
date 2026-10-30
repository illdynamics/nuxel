"""Safety and integration checks for the read-only S10+ speaker diagnostic."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIAG = ROOT / "tools/s10plus/a33/nuxel-cs35l41-speaker-diag.sh"
BUILD = ROOT / "kernel/s10plus/build-kernel.sh"
ROUTE = ROOT / "services/nuxel-s10/bin/nuxel-audio-route.sh"


def test_speaker_diag_help_is_available_without_touching_hardware():
    result = subprocess.run([str(DIAG), "--help"], text=True, capture_output=True, check=False)
    assert result.returncode == 0
    assert "READ-ONLY" in result.stdout
    assert "No playback is initiated" in result.stdout


def test_speaker_diag_uses_read_only_control_reads_only():
    text = DIAG.read_text(encoding="utf-8")
    assert "amixer -c \"$CARD\" cget" in text
    assert "amixer -c \"$CARD\" cset" not in text
    assert "wpctl set-" not in text
    assert "systemctl restart" not in text
    assert "systemctl stop" not in text
    assert "printf on >" not in text
    assert "echo 1 >" not in text
    assert "regmap" in text.lower()
    assert "No audio was played" in text


def test_diag_samples_runtime_pcm_and_dsp_power_telemetry():
    text = DIAG.read_text(encoding="utf-8")
    assert "--watch-seconds" in text
    assert "hw_params" in text
    assert "status" in text
    assert "PL_SPK_OUTPUT_POWER" in text
    assert "L_SPK_OUTPUT_POWER" in text
    assert "SOUNDBOOST_EN" in text
    assert "subprocess.run(['amixer', '-c', card, 'contents']" in text
    assert "speaker_mixer_telemetry" in text
    assert "cirrus_power_sysfs" in text


def test_kernel_wrapper_now_applies_patches_idempotently():
    text = BUILD.read_text(encoding="utf-8")
    assert "apply_kernel_patches()" in text
    assert "git -C \"${KSRC}\" apply --reverse --check" in text
    assert "git -C \"${KSRC}\" apply --check" in text
    assert "patch-application.log" in text
    assert "${patch}.required" in text
    assert "# STUB" in text


def test_route_comment_does_not_claim_acoustic_confirmation():
    text = ROUTE.read_text(encoding="utf-8")
    assert "NOT an acoustically confirmed gain value" in text
    assert "only value that has ever produced confirmed sound" not in text
