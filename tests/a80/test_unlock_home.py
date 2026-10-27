"""Run the shipped lockscreen/Home state-machine harness plus root-cause checks."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_unlock_state_machine_lands_home_and_failed_unlock_stays_locked():
    node = shutil.which("node")
    assert node, "node is required for the launcher state-machine harness"
    proc = subprocess.run(
        [node, str(ROOT / "tools/s10plus/a45/test-lockscreen-unlock.js")],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ALL PASS" in proc.stdout
    for phrase in (
        "successful unlock lands on the canonical Home desktop",
        "successful boot unlock closes a stale Applications drawer",
        "locked deep-link launch is ignored",
        "failed backend unlock does not navigate to Home",
        "post-unlock clears a stale #app route",
    ):
        assert phrase in proc.stdout, phrase


def test_controller_has_explicit_post_unlock_home_transition():
    js = (ROOT / "pwa/nuxel-home/js/app.js").read_text()
    assert "this._enterHomeAfterUnlock(reason || 'unlock');" in js
    assert "unlock:home reason=" in js
    assert "history.replaceState" in js
    # Both app launch paths are gated while the lockscreen is authoritative.
    assert js.count("launch:blocked-locked app=") == 2
