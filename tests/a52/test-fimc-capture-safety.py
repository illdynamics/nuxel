#!/usr/bin/env python3
"""Static safety checks for the FIMC-IS first-light client.

These checks intentionally do not access V4L2 hardware.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/s10plus/fimc-capture/nuxel-fimc-capture.c"


def test_sensor_initialisation_requires_explicit_consent() -> None:
    source = SOURCE.read_text()
    assert "--allow-sensor-init" in source
    assert "refusing sensor init" in source
    assert "O.sensor_probe && !O.allow_sensor_init" in source


def test_zeroed_get_format_cannot_be_reported_as_probe_success() -> None:
    source = SOURCE.read_text()
    assert '"FORMAT_UNCOMMITTED"' in source
    assert "!fmt.fmt.pix_mp.width || !fmt.fmt.pix_mp.height" in source


def test_cleanup_never_retries_failed_streamoff() -> None:
    cleanup = SOURCE.read_text().split('\nfail:\n',1)[1].split('\nout:\n',1)[0]
    assert 'goto fail' not in cleanup
    assert 'if (streaming)' in cleanup
