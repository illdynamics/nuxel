#!/usr/bin/env python3
"""Offline tests for nuxel-displayd's lifecycle and mode controller.

The daemon is exercised with a real fixture sysfs root, a fake systemctl runner
and a fake notification hub.  No device, compositor or framebuffer is touched.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.abspath(os.path.join(HERE, ".."))
LIB = os.path.join(BASE, "lib")
DAEMON = os.path.join(BASE, "bin", "nuxel-displayd")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import nuxel_display as nd  # noqa: E402

_loader = SourceFileLoader("nuxel_displayd", DAEMON)
spec = importlib.util.spec_from_loader("nuxel_displayd", _loader)
daemon_mod = importlib.util.module_from_spec(spec)
_loader.exec_module(daemon_mod)

# Reuse the fixture builder from the model test (kept as a plain module).
mod_spec = importlib.util.spec_from_file_location(
    "test_display_model", os.path.join(HERE, "test-display-model.py"))
model = importlib.util.module_from_spec(mod_spec)
mod_spec.loader.exec_module(model)


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        raise AssertionError(msg)


class FakeNotifier:
    def __init__(self):
        self.submitted = []
        self.archived = []
    def submit(self, payload):
        self.submitted.append(payload)
        return {"success": True, "id": len(self.submitted)}
    def archive(self, nid):
        self.archived.append(nid)
        return {"success": True}


class FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    def __init__(self):
        self.calls = []
        self.ext_state_path = None
    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        if argv[:2] == ["systemctl", "is-active"]:
            return FakeProc(0, "active\n", "")
        if argv[:2] in (["systemctl", "restart"], ["systemctl", "start"]) and self.ext_state_path:
            # The real bridge publishes RUNNING after its first frame.
            with open(self.ext_state_path, "w") as f:
                f.write("state RUNNING mode=mirror output=HEADLESS-1\n")
        return FakeProc(0, "", "")


def make_daemon(pd=True, dp=True, outputs=None, monitor=True):
    root = model.fixture(partner=True, pd=pd, dp=dp, fb=True,
                         audio=True, monitor=monitor)
    run_dir = tempfile.mkdtemp(prefix="nx-display-run-")
    state_dir = tempfile.mkdtemp(prefix="nx-display-state-")
    notifier = FakeNotifier()
    runner = FakeRunner()
    outputs = outputs if outputs is not None else [
        {"name": "HEADLESS-1", "enabled": True, "position": "0,0",
         "width": 720, "height": 1520},
        {"name": "HEADLESS-2", "enabled": True, "position": "720,0",
         "width": 1920, "height": 1080},
    ]
    chosen = nd.choose_outputs(outputs)
    chosen["success"] = True
    chosen["error"] = None
    d = daemon_mod.DisplayDaemon(root=root, run_dir=run_dir,
                                 state_dir=state_dir, poll_interval=0.2,
                                 notifier=notifier, runner=runner)
    # Keep the fake compositor outputs for every refresh on this instance.
    d.refresh_outputs = lambda force=False: chosen
    d.refresh_snapshot(force_outputs=True)
    runner.ext_state_path = os.path.join(run_dir, "ext.state")
    return d, root, run_dir, notifier, runner


def test_poll_notification_and_reconnect():
    d, root, run_dir, notifier, runner = make_daemon()
    # First poll after the state transition settles it; the second emits.
    d.poll_once(now=1.0)
    d.poll_once(now=2.0)
    check(len(notifier.submitted) == 1, "one notification on first DP connection")
    actions = notifier.submitted[0]["actions"]
    check("mirror-portrait" in actions and "mirror-landscape" in actions and
          "fullscreen" in actions and "desktop" in actions,
          "notification carries all four mode actions")
    nid = d.notification_id
    check(nid == 1, "notification id recorded")
    d.poll_once(now=3.0)
    check(len(notifier.submitted) == 1, "duplicate polls do not re-notify")
    # Real disconnect: secdp/extcon go low.
    model.write(root, "sys/class/switch/secdp/state", "0\n")
    model.write(root, "sys/class/extcon/extcon0/state", "DP=0\n")
    d.poll_once(now=4.0)
    d.poll_once(now=5.0)
    check(nid in notifier.archived, "notification archived on disconnect")
    check(d.sm.mode == nd.MODE_OFF, "disconnect resets mode to off")
    # Reconnect: a fresh generation and a fresh notification.
    model.write(root, "sys/class/switch/secdp/state", "1\n")
    model.write(root, "sys/class/extcon/extcon0/state", "DP=1\n")
    d.poll_once(now=6.0)
    d.poll_once(now=7.0)
    check(len(notifier.submitted) == 2, "reconnect submits a new notification")
    check(d.sm.generation == 2, "reconnect created generation 2")


def test_mirror_mode_start_and_stop():
    d, root, run_dir, notifier, runner = make_daemon(pd=True, dp=True)
    # Simulate the bridge reaching RUNNING after systemctl restart.
    with open(os.path.join(run_dir, "ext.state"), "w") as f:
        f.write("state RUNNING mode=mirror output=HEADLESS-1\n")
    r = d.start_mode("mirror")
    check(r["success"] is True, "mirror starts when DP is ready")
    check(r["output"] == "HEADLESS-1", "mirror targets the phone output")
    start_script = os.path.join(run_dir, "ext-start.sh")
    check(os.path.exists(start_script), "mode controller wrote ext-start.sh")
    with open(start_script) as f:
        text = f.read()
    check("--mode mirror-portrait" in text and "--output HEADLESS-1" in text,
          "start script carries mirror-portrait and output")
    check("--auto-orientation" in text and "--orientation-file" in text and
          "--fit fit" in text,
          "automatic mirror uses the live orientation authority and fit")
    check("--color-order argb" in text,
          "DP bridge uses the measured ARGB packing")
    rot = d.set_rotation(90)
    check(rot["success"] is True and d.rotation == 90 and
          d.auto_orientation is False, "rotation is persisted as a manual override")
    with open(start_script) as f:
        text = f.read()
    check("--rotate 90" in text and "--auto-orientation" not in text,
          "manual rotation restarts with 90 degrees and no auto override")
    check(any(c[:2] == ["systemctl", "start"] for c in runner.calls),
          "systemctl start was requested after the stop")
    check(d.sm.mode == nd.MODE_MIRROR_PORTRAIT, "daemon mode is mirror-portrait")
    check(notifier.submitted and notifier.submitted[-1]["summary"] == "External display active",
          "active-mode notification submitted")
    r = d.start_mode("off")
    check(r["success"] is True and d.sm.mode == nd.MODE_OFF, "off stops the external bridge")


def test_bridge_supervisor_restarts_a_dead_bridge():
    d, root, run_dir, notifier, runner = make_daemon(pd=True, dp=True)
    r = d.start_mode("mirror-portrait")
    check(r["success"] is True, "mirror starts for supervisor test")
    starts_before = sum(1 for c in runner.calls if c[:2] == ["systemctl", "start"])
    # Simulate the bridge exiting on a capture failure.
    with open(os.path.join(run_dir, "ext.state"), "w") as f:
        f.write("state STOPPED reason=error frames=10\n")
    d.poll_once(now=10.0)
    starts_after = sum(1 for c in runner.calls if c[:2] == ["systemctl", "start"])
    check(starts_after == starts_before + 1, "supervisor restarts a stopped bridge")
    check(d._ext_state().get("state") == "RUNNING", "supervisor sees the bridge running again")
    check(d.sm.mode == nd.MODE_MIRROR_PORTRAIT, "supervisor keeps the requested mode")


def test_rotation_validation():
    d, root, run_dir, notifier, runner = make_daemon(pd=True, dp=True)
    check(d.set_rotation(45)["success"] is False, "invalid rotation is refused")
    check(d.set_rotation(270)["success"] is True and d.rotation == 270,
          "270 degrees is accepted")


def test_desktop_mode_requires_second_output():
    d, root, run_dir, notifier, runner = make_daemon(
        pd=True, dp=True,
        outputs=[{"name": "HEADLESS-1", "enabled": True, "position": "0,0"}])
    r = d.start_mode("desktop")
    check(r["success"] is False, "desktop refused with one compositor output")
    check(r["error"] == "DESKTOP_OUTPUT_UNAVAILABLE", "exact desktop blocker code")
    check(not any(c[:2] in (["systemctl", "restart"], ["systemctl", "start"])
                  for c in runner.calls),
          "no external bridge started for an unavailable mode")


def test_mode_refused_before_dp():
    d, root, run_dir, notifier, runner = make_daemon(pd=False, dp=False)
    r = d.start_mode("mirror")
    check(r["success"] is False, "mirror refused before PD/DP")
    check(r["error"] == "EXTERNAL_DISPLAY_NOT_READY", "exact not-ready code")
    check("USB-PD identity" in (r.get("detail") or ""),
          "refusal explains the missing USB-PD identity")
    check(not any(c[:2] == ["systemctl", "restart"] for c in runner.calls),
          "no external bridge started when not ready")


def test_desktop_mode_with_second_output():
    d, root, run_dir, notifier, runner = make_daemon(pd=True, dp=True)
    with open(os.path.join(run_dir, "ext.state"), "w") as f:
        f.write("state RUNNING mode=desktop output=HEADLESS-2\n")
    r = d.start_mode("desktop")
    check(r["success"] is True, "desktop starts when a second output exists")
    check(r["output"] == "HEADLESS-2", "desktop targets the second output")
    with open(os.path.join(run_dir, "ext-start.sh")) as f:
        text = f.read()
    check("--mode desktop" in text and "--output HEADLESS-2" in text,
          "desktop start script is correct")


def test_stale_stopped_state_does_not_abort_start():
    d, root, run_dir, notifier, runner = make_daemon(pd=True, dp=True)
    # A previous bridge run left a terminal state behind.  The daemon must
    # not mistake it for the new process failing to start.
    with open(os.path.join(run_dir, "ext.state"), "w") as f:
        f.write("state STOPPED reason=signal frames=1\n")
    r = d.start_mode("mirror")
    check(r["success"] is True, "stale STOPPED state does not abort a new start")
    check(d.sm.mode == nd.MODE_MIRROR_PORTRAIT, "mode is mirror-portrait after a successful start")


def _disconnect(root, d):
    # Start-mode deliberately opens a short self-restart grace window; a real
    # cable pull happens after that.  Skip it for the deterministic test.
    d._link_grace_until = 0.0
    model.write(root, "sys/class/switch/secdp/state", "0\n")
    model.write(root, "sys/class/extcon/extcon0/state", "DP=0\n")
    d.poll_once()
    d.poll_once()


def _reconnect(root, d, force_due=True):
    model.write(root, "sys/class/switch/secdp/state", "1\n")
    model.write(root, "sys/class/extcon/extcon0/state", "DP=1\n")
    d.poll_once()
    d.poll_once()
    if force_due:
        d._restore_next_at = 0.0
        d.poll_once()


def test_reconnect_restores_last_mode():
    d, root, run_dir, notifier, runner = make_daemon(pd=True, dp=True)
    with open(os.path.join(run_dir, "ext.state"), "w") as f:
        f.write("state RUNNING mode=mirror output=HEADLESS-1\n")
    r = d.start_mode("mirror-portrait")
    check(r["success"] is True, "mirror active before reconnect test")
    d.poll_once()  # first poll observes the transition
    d.poll_once()  # second settled poll advances the state machine
    check(d.sm.state == nd.DP_LINK_READY, "state machine sees DP ready")
    starts_before = sum(1 for c in runner.calls if c[:2] == ["systemctl", "start"])
    _disconnect(root, d)
    check(d.last_mode == nd.MODE_MIRROR_PORTRAIT,
          "disconnect preserves the user's last mode")
    check(d.sm.mode == nd.MODE_OFF, "disconnect stops the bridge")
    _reconnect(root, d)
    starts_after = sum(1 for c in runner.calls if c[:2] == ["systemctl", "start"])
    check(starts_after > starts_before,
          "reconnect automatically restarts the external bridge")
    check(d.sm.mode == nd.MODE_MIRROR_PORTRAIT,
          "reconnect restores mirror mode")
    check(d._restore_pending is False, "restore state clears after success")


def test_explicit_off_is_not_restored():
    d, root, run_dir, notifier, runner = make_daemon(pd=True, dp=True)
    with open(os.path.join(run_dir, "ext.state"), "w") as f:
        f.write("state RUNNING mode=mirror output=HEADLESS-1\n")
    d.start_mode("mirror-portrait")
    d.poll_once()
    d.poll_once()
    d.stop_mode("user requested internal-only", remember=True)
    check(d.last_mode == nd.MODE_OFF, "explicit off is persisted")
    starts_before = sum(1 for c in runner.calls if c[:2] == ["systemctl", "start"])
    _disconnect(root, d)
    _reconnect(root, d)
    starts_after = sum(1 for c in runner.calls if c[:2] == ["systemctl", "start"])
    check(starts_after == starts_before,
          "explicit internal-only is not overridden by auto-restore")
    check(d.sm.mode == nd.MODE_OFF, "mode stays off after reconnect")


def test_orientation_authority_is_read():
    d, root, run_dir, notifier, runner = make_daemon(pd=True, dp=True)
    orient_dir = tempfile.mkdtemp(prefix="nx-orient-")
    status_path = os.path.join(orient_dir, "status.json")
    with open(status_path, "w") as f:
        f.write('{"effective_orientation":90,"mode":"landscape",'
                '"auto":false,"display":{"transform":"270","applied":true,'
                '"logical_width":1520,"logical_height":720}}\n')
    old_status, old_persisted = daemon_mod.ORIENT_STATUS, daemon_mod.ORIENT_PERSISTED
    daemon_mod.ORIENT_STATUS, daemon_mod.ORIENT_PERSISTED = status_path, status_path
    try:
        info = d.read_orientation()
    finally:
        daemon_mod.ORIENT_STATUS, daemon_mod.ORIENT_PERSISTED = old_status, old_persisted
    check(info["effective_orientation"] == 90, "orientation authority reads 90")
    check(info["transform"] == 270, "compositor transform is 270")
    check(info["external_rotation"] == 270,
          "external presenter uses the validated transform value")


def test_stale_generation_cannot_restore_new_connection():
    d, root, run_dir, notifier, runner = make_daemon(pd=True, dp=True)
    d._schedule_restore(99, "stale-test")
    starts_before = sum(1 for c in runner.calls if c[:2] == ["systemctl", "start"])
    d._restore_next_at = 0.0
    d._run_restore_if_due()
    starts_after = sum(1 for c in runner.calls if c[:2] == ["systemctl", "start"])
    check(starts_after == starts_before,
          "a restore scheduled for an old generation cannot start the bridge")
    check(d._restore_pending is False, "stale restore is cancelled")


def main():
    print("nuxel-display daemon tests")
    test_poll_notification_and_reconnect()
    test_mirror_mode_start_and_stop()
    test_rotation_validation()
    test_desktop_mode_requires_second_output()
    test_mode_refused_before_dp()
    test_desktop_mode_with_second_output()
    test_stale_stopped_state_does_not_abort_start()
    test_reconnect_restores_last_mode()
    test_explicit_off_is_not_restored()
    test_orientation_authority_is_read()
    test_stale_generation_cannot_restore_new_connection()
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
