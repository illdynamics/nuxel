#!/usr/bin/env python3
"""nuxel-haptics-bridge — the wiring between the button manager / notification
daemon and the S10+ (beyond2lte) haptic actuator.

WHAT THIS IS
    The single translator between EVENTS and HAPTICS. The button manager already
    records every FSM action in its audit log; the notification daemon already
    records every notification in its state file and emits
    org.freedesktop.Notifications.NotificationAdded. This bridge turns those
    events into a named pattern from configs/nuxel/haptics/haptics.json and
    performs it through the GATED programmatic API of nuxel-haptics-diag.sh.

    One switch silences everything: bridge.json:always_on_off_switch. The bridge
    only READS that switch, never flips it. When it is off, no consumer buzzes.

WHAT THIS IS NOT
    * It never buzzes on start, and never during boot: it is a session unit, and
      the request FIFO (/run/nuxel-haptics.cmd) only exists while it runs.
    * It never arms the actuator that the owner has not asked for: patterns come
      from the policy file, not from the event payload.
    * It never writes sysfs itself (the tool owns the node), never writes a
      partition or a block device, never calls heimdall/odin/fastboot, and never
      triggers recovery or download mode.

OFFLINE TESTABILITY
    --root DIR  prefixes every filesystem lookup.
    --dry-run   expands and reports, performs no write, exits.
    --once      process a single event (either `--once-log LINE` or
                `--once-event NAME`) and exit — the form the offline tests use.
    selftest    runs the built-in checks with nothing attached.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_repo(start: str) -> str:
    d = start
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "configs", "nuxel")):
            return d
        d = os.path.dirname(d)
    return ""


REPO = _find_repo(HERE)
DEFAULT_POLICY = "/etc/nuxel/haptics/haptics.json"
DEFAULT_BRIDGE = "/etc/nuxel/haptics/bridge.json"
DEFAULT_TOOL = "/usr/bin/nuxel-haptics-diag.sh"


def log(msg: str) -> None:
    print(msg, flush=True)


class Bridge:
    def __init__(self, args):
        self.args = args
        self.root = args.root
        self.dry_run = args.dry_run
        self.policy = self._load(args.policy or DEFAULT_POLICY,
                                 "configs/nuxel/haptics/haptics.json")
        self.cfg = self._load(args.bridge_config or DEFAULT_BRIDGE,
                              "configs/nuxel/haptics/bridge.json")
        self.tool = args.tool or self._tool_path()
        self.log_path = self.abs(args.log or "/var/log/nuxel/haptics-bridge.log")
        self.rate: dict[str, deque] = {}
        self.seen_ids: set[int] = set()
        self.paused_until = 0.0
        self.emitted = 0
        self.refused = 0
        self._load_seen()

    # ---- paths -----------------------------------------------------------
    def abs(self, p: str) -> str:
        if p.startswith("/"):
            return self.root.rstrip("/") + p
        return os.path.join(self.root, p)

    def _load(self, primary: str, repo_rel: str) -> dict:
        # The installed path is subject to --root; the developer-tree fallback is
        # a real host path inside the repository and is therefore NOT prefixed.
        repo_path = os.path.join(REPO, repo_rel) if REPO else ""
        for cand, prefixed in ((primary, True), (repo_path, False)):
            if not cand:
                continue
            path = self.abs(cand) if prefixed else cand
            if os.path.isfile(path):
                with open(path) as fh:
                    return json.load(fh)
        log("!! cannot read %s (and no developer-tree copy at %s) — no haptics are performed"
            % (primary, repo_path or "n/a"))
        return {}

    def _tool_path(self) -> str:
        for cand in (DEFAULT_TOOL, os.path.join(HERE, "nuxel-haptics-diag.sh")):
            if os.path.isfile(self.abs(cand)):
                return cand
        return DEFAULT_TOOL

    def _load_seen(self) -> None:
        p = self.abs("/run/nuxel/haptics/bridge-seen.json")
        try:
            with open(p) as fh:
                self.seen_ids = set(int(x) for x in json.load(fh).get("ids", []))
        except Exception:
            self.seen_ids = set()

    def _save_seen(self) -> None:
        p = self.abs("/run/nuxel/haptics/bridge-seen.json")
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fh:
                json.dump({"ids": sorted(self.seen_ids)[-80:]}, fh)
        except OSError:
            pass

    # ---- gates -----------------------------------------------------------
    def switch_on(self) -> bool:
        path = self.cfg.get("always_on_off_switch", {}).get(
            "path", "/var/lib/nuxel/haptics/state.json")
        try:
            with open(self.abs(path)) as fh:
                doc = json.load(fh)
            return bool(doc.get("enabled", True))
        except Exception:
            # policy default: enabled. Absence of the state file is not a reason
            # to invent a "disabled" state, and it is not a reason to buzz either:
            # the gate file still has to be armed.
            return bool(self.policy.get("global_switch", {}).get("default_enabled", True))

    def apply_gate(self) -> bool:
        """The bridge is the only thing that arms the programmatic API."""
        gate = self.cfg.get("gate_file", "/run/nuxel/haptics/api-enabled")
        if self.dry_run:
            return True
        try:
            os.makedirs(os.path.dirname(self.abs(gate)), exist_ok=True)
            with open(self.abs(gate), "w") as fh:
                fh.write("armed_by=nuxel-haptics-bridge pid=%d at=%s\n"
                         % (os.getpid(), time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
            return True
        except OSError as exc:
            log("!! cannot arm %s (%s) — every request will refuse instead" % (gate, exc))
            return False

    def drop_gate(self) -> None:
        gate = self.cfg.get("gate_file", "/run/nuxel/haptics/api-enabled")
        if self.dry_run:
            return
        try:
            os.unlink(self.abs(gate))
        except OSError:
            pass

    def quiet_now(self, consumer: str) -> bool:
        q = self.cfg.get("quiet_hours", {})
        if consumer not in q.get("applies_to", []):
            return False
        now = time.localtime()
        hhmm = now.tm_hour * 60 + now.tm_min
        for w in q.get("windows", []):
            try:
                sh, sm = (int(x) for x in str(w.get("from", "0:0")).split(":"))
                eh, em = (int(x) for x in str(w.get("to", "0:0")).split(":"))
            except ValueError:
                continue
            start, end = sh * 60 + sm, eh * 60 + em
            if start <= end:
                if start <= hhmm < end:
                    return True
            elif hhmm >= start or hhmm < end:  # window crosses midnight
                return True
        return False

    def rate_ok(self, consumer: str) -> bool:
        rl = self.cfg.get("rate_limit", {})
        win = int(rl.get("window_ms", 10000)) / 1000.0
        mx = int(rl.get("max_per_window", 4))
        now = time.time()
        q = self.rate.setdefault(consumer, deque())
        while q and now - q[0] > win:
            q.popleft()
        if len(q) >= mx:
            return False
        q.append(now)
        return True

    # ---- emit ------------------------------------------------------------
    def emit(self, pattern: str, consumer: str, why: str) -> int:
        if self.paused_until > time.time():
            self.refused += 1
            log("suppress(%s): bridge paused by an owner 'off' request" % consumer)
            return 0
        if not pattern:
            self.refused += 1
            log("refuse(%s): no pattern mapped for %s" % (consumer, why))
            return 0
        if not self.switch_on():
            self.refused += 1
            log("refuse(%s): global haptics switch is OFF — nothing buzzes (%s)" % (consumer, why))
            return 0
        if self.quiet_now(consumer):
            self.refused += 1
            log("suppress(%s): quiet hours (%s)" % (consumer, why))
            return 0
        if not self.rate_ok(consumer):
            self.refused += 1
            log("refuse(%s): bridge rate limit reached (%s)" % (consumer, why))
            return 0
        if self.dry_run:
            self.emitted += 1
            log("emit(%s): pattern=%s (%s) [dry-run]" % (consumer, pattern, why))
            return 0
        rc = self._call_tool(pattern, consumer)
        if rc == 0:
            self.emitted += 1
            log("emit(%s): pattern=%s (%s)" % (consumer, pattern, why))
        else:
            self.refused += 1
            log("refuse(%s): tool returned rc=%d for pattern=%s (%s)" % (consumer, rc, pattern, why))
        return rc

    def _call_tool(self, pattern: str, consumer: str) -> int:
        if not os.path.isfile(self.abs(self.tool)):
            log("!! haptics tool %s is not installed — no buzz" % self.tool)
            return 127
        cmd = [self.tool, "--root", self.root, "api", pattern, "--source", consumer]
        try:
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=20).returncode
        except Exception as exc:  # never let a haptics failure kill the session
            log("!! tool invocation failed: %s" % exc)
            return 126

    # ---- consumers -------------------------------------------------------
    def pattern_for_action(self, action: str) -> str:
        c = self.cfg.get("consumers", {}).get("buttons", {})
        if not c.get("enabled", True):
            return ""
        if action in c.get("ignore_actions", []):
            return ""
        return c.get("action_patterns", {}).get(action, c.get("default_pattern", "button"))

    def handle_buttons_line(self, line: str) -> int:
        c = self.cfg.get("consumers", {}).get("buttons", {})
        rx = c.get("line_regex", r"FSM_ACTION source=(?P<source>\S+) action=(?P<action>\S+)")
        m = re.search(rx, line)
        if not m:
            return 1
        action = m.groupdict().get("action", "")
        return self.emit(self.pattern_for_action(action), "buttons", "action=%s" % action)

    def handle_notification(self, notif: dict, first_pass: bool) -> None:
        c = self.cfg.get("consumers", {}).get("notifications", {})
        try:
            nid = int(notif.get("id", 0))
        except (TypeError, ValueError):
            return
        new = nid not in self.seen_ids
        self.seen_ids.add(nid)
        if first_pass or not new:
            # Establish the baseline WITHOUT buzzing: a bridge restart must never
            # replay the notification history as haptics.
            return
        if not c.get("enabled", True):
            return
        if notif.get("app_id", "") in c.get("skip_app_ids", []):
            log("skip(notifications): app_id=%s" % notif.get("app_id"))
            return
        urgency = str(notif.get("urgency", "normal"))
        pattern = c.get("per_urgency_patterns", {}).get(urgency, c.get("default_pattern", "notify"))
        self.emit(pattern, "notifications", "id=%d app=%s urgency=%s" % (nid, notif.get("app_id", "?"), urgency))
        self._save_seen()

    def poll_notifications(self, first_pass: bool) -> None:
        c = self.cfg.get("consumers", {}).get("notifications", {})
        path = self.abs(c.get("state_file", "/var/lib/nuxel/notifications.json"))
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except Exception:
            return
        entries = doc if isinstance(doc, list) else doc.get("notifications", doc.get("history", []))
        if not isinstance(entries, list):
            return
        for n in entries:
            if isinstance(n, dict):
                self.handle_notification(n, first_pass)

    def handle_fifo_line(self, line: str) -> int:
        d = self.cfg.get("fifo_protocol", {}).get("lines", {})
        toks = line.strip().split()
        if not toks:
            return 1
        verb = toks[0]
        if verb == "pattern" and len(toks) > 1:
            return self.emit(toks[1], "fifo", "pattern request")
        if verb == "button" and len(toks) > 1:
            return self.emit(self.pattern_for_action(toks[1]), "buttons", "fifo action=%s" % toks[1])
        if verb == "notify":
            urg = toks[1] if len(toks) > 1 else "normal"
            c = self.cfg["consumers"]["notifications"]
            return self.emit(c.get("per_urgency_patterns", {}).get(urg, c.get("default_pattern", "notify")),
                             "notifications", "fifo urgency=%s" % urg)
        if verb == "alarm":
            c = self.cfg["consumers"]["alarm"]
            return self.emit(c.get("default_pattern", "alarm"), "alarm", "fifo alarm")
        if verb == "off":
            self.paused_until = time.time() + 30
            log("paused: no haptics for 30 s (owner 'off' request; the persisted switch is unchanged)")
            return 0
        if verb == "status":
            self.status()
            return 0
        log("ignore(fifo): %r is not in fifo_protocol.lines (%s)" % (line.strip(), ", ".join(sorted(d)) or "none"))
        return 2

    # ---- status ----------------------------------------------------------
    def status(self) -> None:
        c = self.cfg.get("consumers", {})
        log("bridge config : %s" % (self.args.bridge_config or DEFAULT_BRIDGE))
        log("tool          : %s" % self.tool)
        log("global switch : %s (read-only for the bridge)"
            % ("ON" if self.switch_on() else "OFF — every consumer refuses"))
        log("gate          : %s" % ("armed" if os.path.exists(self.abs(self.cfg.get("gate_file", ""))) else "closed"))
        for name in ("buttons", "notifications", "alarm"):
            cc = c.get(name, {})
            log("consumer %-13s enabled=%s source=%s pattern=%s"
                % (name, cc.get("enabled", True), cc.get("source", "?"),
                   cc.get("default_pattern", "?")))
        log("emitted=%d refused=%d" % (self.emitted, self.refused))
        log("felt haptics  : NEEDS_OWNER_TEST (%s)" % self.cfg.get("owner_test", {}).get("manual", ""))

    # ---- run loops -------------------------------------------------------
    def run_once(self) -> int:
        if self.args.once_log is not None:
            return self.handle_buttons_line(self.args.once_log)
        if self.args.once_event is not None:
            ev = self.args.once_event
            if ev.startswith("notify"):
                return self.emit("notify", "notifications", "once-event=%s" % ev)
            return self.emit(self.pattern_for_action(ev), "buttons", "once-event=%s" % ev)
        if self.args.once_fifo is not None:
            return self.handle_fifo_line(self.args.once_fifo)
        return 2

    def follow(self, seconds: float) -> int:
        log(self.status.__doc__ or "nuxel-haptics-bridge: NO BUZZ ON START (existing notifications are baselined, not replayed)")
        self.status()
        self.apply_gate()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: sys.exit(0))
        logpath = self.abs(self.cfg["consumers"]["buttons"].get("log", "/var/log/nuxel/buttons.log"))
        fifo = self.abs(self.cfg.get("request_fifo", "/run/nuxel-haptics.cmd"))
        try:
            if not self.dry_run:
                os.makedirs(os.path.dirname(fifo), exist_ok=True)
                if not os.path.exists(fifo):
                    os.mkfifo(fifo, 0o600)
        except OSError as exc:
            log("!! cannot create request FIFO %s (%s)" % (fifo, exc))
        fh = None
        try:
            fh = open(logpath, "r")
            fh.seek(0, os.SEEK_END)
        except OSError:
            log("note: %s is not readable yet — button haptics start when it appears" % logpath)
        fifo_fh = None
        try:
            fifo_fh = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            fifo_fh = None
        self.poll_notifications(first_pass=True)
        deadline = time.time() + seconds if seconds else None
        buf = b""
        try:
            while True:
                if deadline and time.time() >= deadline:
                    return 0
                if fh is None:
                    try:
                        fh = open(logpath, "r")
                        fh.seek(0, os.SEEK_END)
                    except OSError:
                        pass
                if fh is not None:
                    line = fh.readline()
                    if line:
                        self.handle_buttons_line(line.rstrip("\n"))
                if fifo_fh is not None:
                    try:
                        chunk = os.read(fifo_fh, 4096)
                    except OSError:
                        chunk = b""
                    if chunk:
                        buf += chunk
                        while b"\n" in buf:
                            raw, buf = buf.split(b"\n", 1)
                            if raw.strip():
                                self.handle_fifo_line(raw.decode("utf-8", "replace"))
                self.poll_notifications(first_pass=False)
                time.sleep(0.25)
        finally:
            sys.stdout.flush()
            try:
                if fifo_fh is not None:
                    os.close(fifo_fh)
            except OSError:
                pass
            self.drop_gate()
            log("bridge stopped: gate disarmed (system requests now refuse)")

    def selftest(self) -> int:
        import tempfile
        rc = 0
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "sys/class/leds/vibrator"), exist_ok=True)
            with open(os.path.join(td, "sys/class/leds/vibrator/activate"), "w") as fh:
                fh.write("0")
            os.makedirs(os.path.join(td, "etc/nuxel/haptics"), exist_ok=True)
            os.chmod(os.path.join(td, "sys/class/leds/vibrator/activate"), 0o600)
            a = argparse.Namespace(root=td, policy=None, bridge_config=None, tool=None,
                                   log=None, dry_run=True, once_log=None, once_event=None,
                                   once_fifo=None, follow=False, seconds=0, status=False,
                                   selftest=True)
            b = Bridge(a)
            checks = [
                ("maps volume-up -> button", b.pattern_for_action("volume-up") == "button"),
                ("maps screen-lock -> gesture", b.pattern_for_action("screen-lock") == "gesture"),
                ("ignores refused poweroff", b.pattern_for_action("poweroff") == ""),
                ("ignores refused download mode", b.pattern_for_action("boot-download-mode") == ""),
                ("parses the manager audit line",
                 b.handle_buttons_line("2026-10-16T12:00:00Z FSM_ACTION source=key action=screen-lock") == 0),
                ("drops an unrelated line",
                 b.handle_buttons_line("MANAGER_READY key=/dev/input/event0") == 1),
                ("rejects a bogus fifo line", b.handle_fifo_line("echo 1 > /dev/mmcblk0") == 2),
            ]
            for name, ok in checks:
                print(("PASS " if ok else "FAIL ") + name)
                rc |= 0 if ok else 1
            # switch OFF must silence everything even with the gate armed
            os.makedirs(os.path.join(td, "var/lib/nuxel/haptics"), exist_ok=True)
            with open(os.path.join(td, "var/lib/nuxel/haptics/state.json"), "w") as fh:
                json.dump({"enabled": False}, fh)
            b.emitted = b.refused = 0
            b.emit("notify", "notifications", "selftest")
            ok = b.emitted == 0 and b.refused == 1
            print(("PASS " if ok else "FAIL ") + "global switch OFF silences notifications")
            rc |= 0 if ok else 1
            with open(os.path.join(td, "var/lib/nuxel/haptics/state.json"), "w") as fh:
                json.dump({"enabled": True}, fh)
            b.emitted = b.refused = 0
            b.emit("notify", "notifications", "selftest")
            ok = b.emitted == 1
            print(("PASS " if ok else "FAIL ") + "switch ON emits (dry-run, no hardware write)")
            rc |= 0 if ok else 1
            b.emitted = b.refused = 0
            for i in range(9):
                b.emit("tap", "buttons", "burst %d" % i)
            ok = b.refused >= 1
            print(("PASS " if ok else "FAIL ") + "bridge rate limit engages on a burst")
            rc |= 0 if ok else 1
            first = {"id": 1, "app_id": "nuxel-clock", "urgency": "critical"}
            b.emitted = b.refused = 0
            b.handle_notification(first, first_pass=True)
            ok = b.emitted == 0
            print(("PASS " if ok else "FAIL ") + "no buzz on start (history is baselined, not replayed)")
            rc |= 0 if ok else 1
            b.emitted = b.refused = 0
            b.handle_notification({"id": 2, "app_id": "nuxel-clock", "urgency": "critical"}, first_pass=False)
            ok = b.emitted == 1
            print(("PASS " if ok else "FAIL ") + "a NEW critical notification buzzes (alarm pattern)")
            rc |= 0 if ok else 1
            b.emitted = b.refused = 0
            b.handle_notification({"id": 3, "app_id": "nuxel-haptics", "urgency": "normal"}, first_pass=False)
            ok = b.emitted == 0
            print(("PASS " if ok else "FAIL ") + "the haptics tool's own output never buzzes")
            rc |= 0 if ok else 1
        print("ALL HAPTICS BRIDGE OFFLINE CHECKS PASS" if rc == 0 else "FAILURES ABOVE")
        return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="S10+ haptics wiring bridge (button manager + notifications)")
    ap.add_argument("--root", default=os.environ.get("NUXEL_HAPTICS_ROOT", "/"))
    ap.add_argument("--policy", default=None, help="haptics.json (default /etc/nuxel/haptics/haptics.json)")
    ap.add_argument("--bridge-config", default=None, help="bridge.json (default /etc/nuxel/haptics/bridge.json)")
    ap.add_argument("--tool", default=None, help="nuxel-haptics-diag.sh path")
    ap.add_argument("--log", default=None)
    ap.add_argument("--dry-run", action="store_true", help="report decisions, perform no write")
    ap.add_argument("--once-log", default=None, help="process one button-manager audit line and exit")
    ap.add_argument("--once-event", default=None, help="process one event name (e.g. volume-up) and exit")
    ap.add_argument("--once-fifo", default=None, help="process one request-FIFO line and exit")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--follow", action="store_true", help="run the session loop")
    ap.add_argument("--seconds", type=float, default=0, help="with --follow: bounded run (testing)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    b = Bridge(args)
    if args.selftest:
        return b.selftest()
    if args.status:
        b.status()
        return 0
    if args.once_log is not None or args.once_event is not None or args.once_fifo is not None:
        return b.run_once()
    if args.follow:
        return b.follow(args.seconds)
    b.status()
    log("nothing to do: pass --follow to run the session bridge, --once-* / --selftest for the offline checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
