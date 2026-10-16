#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""tor-control.py - read real Tor state over the control port (cookie auth).

Why this exists: "tor.service is active" is NOT evidence that traffic is being
routed through Tor. The only device-side evidence that a circuit exists is the
control port's answer to `GETINFO circuit-status`, and this is the smallest
honest client for it - no `stem` dependency, no third-party code, no writes.

Usage:
  tor-control.py --host 127.0.0.1 --port 9051 [--cookie FILE] [--timeout S] \
                 [--json] circuits|status|version

Exit codes: 0 ok, 2 connection/auth failure, 3 protocol error, 4 usage.

It never claims anonymisation: it reports what the control port said, including
the circuit IDs, their purpose, their state and the relay fingerprints - which
is exactly the evidence a human needs to decide whether to trust it.
"""
import argparse
import binascii
import json
import socket
import sys
import time

EXIT_OK = 0
EXIT_CONN = 2
EXIT_PROTO = 3
EXIT_USAGE = 4
DEFAULT_COOKIE = "/run/tor/control.authcookie"


class ControlError(Exception):
    pass


def _readline(fh):
    line = fh.readline()
    if not line:
        raise ControlError("control connection closed by tor")
    return line.rstrip("\r\n")


class TorControl(object):
    def __init__(self, host, port, cookie, timeout):
        self.host = host
        self.port = port
        self.cookie = cookie
        self.timeout = timeout
        self.sock = None
        self.fh = None

    def __enter__(self):
        try:
            self.sock = socket.create_connection((self.host, self.port), self.timeout)
        except OSError as exc:
            raise ControlError("cannot connect to %s:%s (%s)" % (self.host, self.port, exc))
        self.sock.settimeout(self.timeout)
        self.fh = self.sock.makefile("rwb", buffering=0)
        return self

    def __exit__(self, *exc):
        try:
            if self.fh:
                self.fh.close()
            if self.sock:
                self.sock.close()
        except OSError:
            pass
        return False

    def send(self, line):
        self.fh.write((line + "\r\n").encode("ascii"))

    def read_reply(self):
        """Return (code, [lines]). Raises on protocol errors."""
        code = None
        lines = []
        while True:
            line = _readline(self.fh)
            if len(line) < 4:
                raise ControlError("short reply: %r" % line)
            status, sep, rest = line[:3], line[3], line[4:]
            if not status.isdigit():
                raise ControlError("bad reply code: %r" % line)
            if code is None:
                code = status
            elif not status.startswith(code[0]):
                raise ControlError("inconsistent reply codes: %s then %s" % (code, status))
            if sep == "+":
                lines.append(rest)
            if sep == " ":
                return code, lines

    def authenticate(self):
        try:
            with open(self.cookie, "rb") as fh:
                raw = fh.read()
        except (IOError, OSError) as exc:
            raise ControlError("cannot read cookie %s (%s)" % (self.cookie, exc))
        self.send("AUTHENTICATE " + binascii.hexlify(raw).decode("ascii"))
        code, lines = self.read_reply()
        if code != "250":
            raise ControlError("AUTHENTICATE failed: %s %s" % (code, " ".join(lines)))

    def getinfo(self, key):
        self.send("GETINFO " + key)
        code, lines = self.read_reply()
        if code != "250":
            raise ControlError("GETINFO %s failed: %s %s" % (key, code, " ".join(lines)))
        out = []
        for line in lines:
            if line.startswith(key + "="):
                out.append(line[len(key) + 1:])
            elif line == "OK" or line.endswith("="):
                out.append(line)
        return "\n".join(out)


def parse_circuits(raw):
    """Parse circuit-status into structured, evidence-friendly records."""
    circuits = []
    for line in raw.splitlines():
        parts = line.split()
        if not parts:
            continue
        rec = {"id": parts[0], "state": parts[1] if len(parts) > 1 else "UNKNOWN",
               "purpose": parts[2] if len(parts) > 2 else "UNKNOWN"}
        for token in parts[3:]:
            if "=" in token:
                key, _, value = token.partition("=")
                rec[key] = value
        circuits.append(rec)
    return circuits


def main():
    ap = argparse.ArgumentParser(description="read Tor control-port state (read-only)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9051)
    ap.add_argument("--cookie", default=DEFAULT_COOKIE)
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("command", choices=["circuits", "status", "version"])
    args = ap.parse_args()

    try:
        with TorControl(args.host, args.port, args.cookie, args.timeout) as ctl:
            ctl.authenticate()
            version = ctl.getinfo("version")
            if args.command == "version":
                payload = {"version": version, "source": "control-port"}
            else:
                raw = ctl.getinfo("circuit-status")
                circuits = parse_circuits(raw)
                built = [c for c in circuits if c.get("state") == "BUILT"]
                payload = {
                    "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "version": version,
                    "control_port_authenticated": True,
                    "circuits_total": len(circuits),
                    "circuits_built": len(built),
                    "circuits": circuits if args.command == "circuits" else built,
                    "source": "control-port GETINFO circuit-status",
                    "honest_note": ("A built circuit is evidence that Tor has a path. It is NOT "
                                    "evidence that this device's traffic uses it, and it says "
                                    "nothing about exit-node trustworthiness."),
                }
    except ControlError as exc:
        payload = {
            "control_port_authenticated": False,
            "error": str(exc),
            "circuits_built": None,
            "source": "control-port (unavailable)",
            "honest_note": "Without the control port the tool cannot show circuits; it reports null, never a guess.",
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("tor control port: %s" % exc, file=sys.stderr)
        return EXIT_CONN

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if payload.get("control_port_authenticated"):
            print("tor version: %s" % payload["version"])
            print("circuits built: %s of %s" % (payload["circuits_built"], payload["circuits_total"]))
            for c in payload.get("circuits", []):
                print("  id=%s state=%s purpose=%s" % (c.get("id"), c.get("state"), c.get("purpose")))
        else:
            print("tor control port unavailable: %s" % payload.get("error"), file=sys.stderr)
            return EXIT_CONN
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
