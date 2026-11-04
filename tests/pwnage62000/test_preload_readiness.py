#!/usr/bin/env python3
"""PWNAGE-62000 preload readiness/timing regressions."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROLLER = ROOT / "services/nuxel-preload-cinema/nuxel-preload-cinema"

loader = importlib.machinery.SourceFileLoader("preload_p62000", str(CONTROLLER))
spec = importlib.util.spec_from_loader("preload_p62000", loader)
mod = importlib.util.module_from_spec(spec)
sys.modules["preload_p62000"] = mod
loader.exec_module(mod)

# Reuse the established fake-mpv harness rather than inventing a second one.
spec2 = importlib.util.spec_from_file_location(
    "test_preload_cinema_p31000", ROOT / "tests/pwnage31000/test_preload_cinema.py")
harness_mod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(harness_mod)
Harness = harness_mod.Harness

FAIL = []


def check(cond, msg, extra=None):
    print(("PASS " if cond else "FAIL ") + msg + ("" if cond or extra is None else "  " + str(extra)))
    if not cond:
        FAIL.append(msg)


def with_env(**values):
    saved = {k: os.environ.get(k) for k in values}
    for k, v in values.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = str(v)
    return saved


def restore_env(saved):
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_config_precedence(tmp_path: Path):
    cfg = {
        "schema_version": 1, "enabled": True,
        "early_wait_launcher_ms": 4000, "early_map_delay_ms": 1200,
        "final_frame_grace_ms": 1500, "max_display_ms": 12000,
        "hard_timeout_ms": 15000,
    }
    path = tmp_path / "preload.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg))
    saved = with_env(NUXEL_PRELOAD_CONFIG=str(path),
                     NUXEL_PRELOAD_EARLY_WAIT_LAUNCHER_MS=None,
                     NUXEL_PRELOAD_EARLY_MAP_DELAY_MS=None,
                     NUXEL_PRELOAD_FINAL_FRAME_GRACE_MS=None)
    try:
        c = mod.load_config([])
        check(c.get("early_wait_launcher_ms") == 4000,
              "JSON early_wait_launcher_ms is authoritative (no shell override)", c.get("early_wait_launcher_ms"))
        check(c.get("early_map_delay_ms") == 1200,
              "JSON early_map_delay_ms is authoritative (no shell override)", c.get("early_map_delay_ms"))
        check(c.get("final_frame_grace_ms") == 1500,
              "final_frame_grace_ms is loaded", c.get("final_frame_grace_ms"))
    finally:
        restore_env(saved)

    saved = with_env(NUXEL_PRELOAD_CONFIG=str(path),
                     NUXEL_PRELOAD_EARLY_WAIT_LAUNCHER_MS="2500",
                     NUXEL_PRELOAD_EARLY_MAP_DELAY_MS="700")
    try:
        c = mod.load_config([])
        check(c.get("early_wait_launcher_ms") == 2500,
              "explicit operator env override is honored", c.get("early_wait_launcher_ms"))
        check(c.get("early_map_delay_ms") == 700,
              "explicit operator map delay override is honored", c.get("early_map_delay_ms"))
    finally:
        restore_env(saved)

    saved = with_env(NUXEL_PRELOAD_CONFIG=str(path),
                     NUXEL_PRELOAD_EARLY_WAIT_LAUNCHER_MS="not-a-number")
    try:
        c = mod.load_config([])
        check(c.get("early_wait_launcher_ms") == 4000,
              "invalid env value falls back to the JSON/default value", c.get("early_wait_launcher_ms"))
    finally:
        restore_env(saved)


def test_session_script_has_no_duplicate_timing_defaults():
    text = (ROOT / "tools/s10plus/a45/nuxel-session.sh").read_text()
    check("NUXEL_PRELOAD_EARLY_WAIT_LAUNCHER_MS:-" not in text,
          "session script does not inject a duplicate launcher-wait default")
    check("NUXEL_PRELOAD_EARLY_MAP_DELAY_MS:-" not in text,
          "session script does not inject a duplicate map-delay default")


def test_touch_is_not_a_presentation_gate(tmp_path: Path):
    h = Harness(tmp_path, touch=True,
                extra_config={"readiness_grace_ms": 5000,
                              "max_display_ms": 3000,
                              "hard_timeout_ms": 8000})
    # Touch is present but has not settled: the old code would hold the final
    # video frame for the 5 s readiness grace.  Presentation is already safe.
    h.touch_state.write_text("2026-11-03T00:00:00Z TOUCH_SCAN_START retry=1\n")
    out = h.run(timeout=10, FAKE_MPV_EOF_MS="150")
    check(out.returncode == 0, "controller exits successfully with delayed touch", out.stderr)
    r = h.receipt_doc()
    check(r.get("reason") == "video-eof-and-presentation-ready",
          "video releases at EOF on presentation readiness", r.get("reason"))
    check(r.get("presentation_ready") is True and r.get("input_ready") is False,
          "receipt distinguishes presentation_ready from input_ready",
          (r.get("presentation_ready"), r.get("input_ready")))
    check(float(r.get("elapsed_s") or 99) < 3.0,
          "delayed touch no longer freezes the final frame", r.get("elapsed_s"))
    check(r.get("final_frame_hold_s") is not None,
          "receipt records the final-frame hold duration", r.get("final_frame_hold_s"))


def test_readiness_object():
    r = mod.Readiness(launcher_ready=True, boot_os=True, wlfb_ready=True,
                      display_on=True, touch_settled=False, touch_unknown=False)
    check(r.ready is True and r.critical is True,
          "Readiness.ready means presentation readiness, not touch readiness")
    check(r.input_ready is False,
          "input readiness remains separately false")


def check_bootstrap_guard():
    root = Path(__file__).resolve().parents[2]
    text = (root / "services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh").read_text()
    block = text.split("install_preload() {", 1)[1].split("files_only()", 1)[0]
    check("nuxel-preload-cinema" in block and "-nt /usr/lib/nuxel/nuxel-preload-cinema" in block,
          "cold-boot bootstrap cannot revert a newer preload controller")
    check("kept newer deployed /usr/lib/nuxel/nuxel-preload-cinema" in block,
          "cold-boot bootstrap records the kept-newer decision")


def main():
    check_bootstrap_guard()
    import tempfile
    with tempfile.TemporaryDirectory(prefix="p62000-preload-") as td:
        test_config_precedence(Path(td) / "cfg")
        # test_config_precedence needs the directory
    test_session_script_has_no_duplicate_timing_defaults()
    test_readiness_object()
    with tempfile.TemporaryDirectory(prefix="p62000-preload-run-") as td:
        test_touch_is_not_a_presentation_gate(Path(td))
    print("\n" + ("ALL PASS" if not FAIL else "%d FAILURES" % len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
