"""PWNAGE-58000 contracts: idle tuning is installed, bounded and honest.

These are source/build contracts, not physical measurements.  The prompt files
must also say so, so a future agent cannot turn this suite green into a claim of
measured battery life.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh"
SERVICE = ROOT / "services/nuxel-performance/systemd/nuxel-perf-tune.service"
SCRIPT = ROOT / "services/nuxel-performance/bin/nuxel-perf-tune.sh"
JOURNALD = ROOT / "configs/nuxel/performance/journald.conf"
ROOTFS_VERIFIER = ROOT / "tools/s10plus/verify-fedora-phone-rootfs.py"
SERVICE_GRAPH = ROOT / "tools/s10plus/a33/verify-service-graph.py"
FULL_PROMPT = ROOT / "full-pwnage-58000.md"
KICKSTART_PROMPT = ROOT / "pwnage-58000.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_builder_installs_and_enables_perf_service():
    text = read(BUILDER)
    assert "/nuxel/services/nuxel-performance/bin/nuxel-perf-tune.sh" in text
    assert '"$STAGE/usr/lib/nuxel/nuxel-perf-tune.sh"' in text
    assert "/nuxel/services/nuxel-performance/systemd/nuxel-perf-tune.service" in text
    assert '"$STAGE/etc/systemd/system/nuxel-perf-tune.service"' in text
    assert "ln -sf ../nuxel-perf-tune.service" in text
    assert "multi-user.target.wants/nuxel-perf-tune.service" in text


def test_builder_installs_journald_dropin_not_global_policy():
    text = read(BUILDER)
    assert "install -d \"$STAGE/etc/systemd/journald.conf.d\"" in text
    assert "/nuxel/configs/nuxel/performance/journald.conf" in text
    assert '"$STAGE/etc/systemd/journald.conf.d/50-nuxel-performance.conf"' in text
    # A drop-in is the intended shape; rewriting the packaged journald.conf
    # would be clobbered by the next systemd RPM update.
    assert '"$STAGE/etc/systemd/journald.conf"' not in text


def test_rootfs_verifier_requires_the_exact_wired_bytes():
    text = read(ROOTFS_VERIFIER)
    for needle in (
        "'/usr/lib/nuxel/nuxel-perf-tune.sh'",
        "'/etc/systemd/system/nuxel-perf-tune.service'",
        "'/etc/systemd/system/multi-user.target.wants/nuxel-perf-tune.service'",
        "'/etc/systemd/journald.conf.d/50-nuxel-performance.conf'",
    ):
        assert needle in text, needle
    assert "'/usr/lib/nuxel/nuxel-perf-tune.sh': 'services/nuxel-performance/bin/nuxel-perf-tune.sh'" in text
    assert "'/etc/systemd/system/nuxel-perf-tune.service': 'services/nuxel-performance/systemd/nuxel-perf-tune.service'" in text
    assert "'/etc/systemd/journald.conf.d/50-nuxel-performance.conf': 'configs/nuxel/performance/journald.conf'" in text


def test_service_graph_tracks_the_new_unit():
    text = read(SERVICE_GRAPH)
    assert "services/nuxel-performance/systemd/nuxel-perf-tune.service" in text


def test_service_unit_is_a_safe_oneshot():
    text = read(SERVICE)
    assert "Type=oneshot" in text
    assert "ExecStart=/usr/lib/nuxel/nuxel-perf-tune.sh" in text
    assert "ConditionPathExists=/usr/lib/nuxel/nuxel-perf-tune.sh" in text
    assert "RemainAfterExit=yes" in text
    assert "TimeoutStartSec=20" in text
    assert "WantedBy=multi-user.target" in text
    assert "Nice=10" in text


def test_tuning_script_only_touches_declared_userspace_knobs():
    text = read(SCRIPT)
    assert "dirty_writeback_centisecs=1500" in text
    assert "dirty_expire_centisecs=4500" in text
    assert "vm.swappiness=10" in text
    assert "rotational" in text and "noop" in text
    # Check executable lines only: the header comment explicitly says these
    # subsystems are NOT touched, so a raw substring scan would be wrong.
    code = "\n".join(
        line.split("#", 1)[0] for line in text.splitlines()
    )
    for forbidden in (
        "scaling_governor", "watchdog", "softdog", "dd if=",
        "mkfs", "mount ", "reboot", "poweroff", "thermal_zone",
    ):
        assert forbidden not in code, forbidden
    proc = subprocess.run(["sh", "-n", str(SCRIPT)], check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_journald_policy_is_bounded_and_not_a_fsync_every_line():
    text = read(JOURNALD)
    assert "[Journal]" in text
    assert re.search(r"^SystemMaxUse=512M$", text, re.M)
    assert re.search(r"^SystemMaxFileSize=64M$", text, re.M)
    assert re.search(r"^RuntimeMaxUse=64M$", text, re.M)
    assert re.search(r"^SyncIntervalSec=5m$", text, re.M)
    assert "Storage=" not in text  # do not silently switch journal storage modes


def test_prompts_exist_and_do_not_claim_measurements():
    for path in (FULL_PROMPT, KICKSTART_PROMPT):
        assert path.is_file(), path
        text = read(path)
        assert "PWNAGE-58000" in text
        assert "idle" in text.lower()
        assert "wake" in text.lower()
        assert "not measured" in text.lower() or "unmeasured" in text.lower()
        assert "794c879" in text
        assert "journald" in text.lower()
        assert "nuxel-perf-tune" in text


def test_full_prompt_is_operational_not_a_summary():
    text = read(FULL_PROMPT)
    required = (
        "# 0. Mission",
        "# 2. Non-negotiable operating rules",
        "# 5. Measurement methodology",
        "# 8. Regression matrix",
        "# 10. Acceptance criteria",
        "# 11. Deliverables",
        "/proc/interrupts",
        "/proc/stat",
        "wakeup_count",
        "systemd-analyze",
        "journalctl --verify",
        "physical handset",
        "rollback",
        "no kernel flash",
    )
    for needle in required:
        assert needle in text, needle


def test_kickstarter_prompt_is_a_real_start_prompt():
    text = read(KICKSTART_PROMPT)
    for needle in (
        "Mission",
        "Starting state",
        "First 30 minutes",
        "Acceptance",
        "Deliverables",
        "Do not",
        "nuxel-perf-tune.service",
        "50-nuxel-performance.conf",
    ):
        assert needle in text, needle


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as exc:
                failures.append((name, str(exc)))
                print("FAIL", name, exc)
    print("PWNAGE-58000 TESTS:", "ALL PASS" if not failures else "FAILURES")
    raise SystemExit(1 if failures else 0)
