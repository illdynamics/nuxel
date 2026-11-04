#!/usr/bin/env python3
"""nuxel-nfc: one least-privilege owner of /dev/sec-nfc.

Default-off.  The device is opened only for an explicit enable or scan request.
The daemon never writes tags, never enters BOOTLOADER/NPT mode, never touches
the secure element and never persists tag UID/NDEF data by default.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import stat
import struct
import sys
import threading
import time
import traceback

from . import abi, inventory, ndef, nci
from .transport import SecNfcTransport, TransportError

SCHEMA = "nuxel.nfc-daemon/1"
STATUS_SCHEMA = "nuxel.nfc-status/2"
MAX_REQUEST = 16384


def _atomic_json(path, doc, mode=0o600):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    tmp = "%s.tmp.%d" % (path, os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(doc, fh, sort_keys=True, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


class NfcDaemon:
    def __init__(self, transport=None, root="/", state_path=None):
        self.lock = threading.RLock()
        self.transport = transport or SecNfcTransport()
        self.root = root
        self.state_path = state_path or abi.STATE_PATH
        self.state = "OFF"
        self.last_error = None
        self.last_tag = None
        self.last_scan_started = 0.0
        self.last_scan_finished = 0.0
        self.controller = None
        self._cancel = threading.Event()
        self._write_state()

    def _write_state(self):
        doc = {
            "schema": SCHEMA,
            "state": self.state,
            "enabled": self.state in ("READY", "SCANNING", "TAG_PRESENT"),
            "last_error": self.last_error,
            "last_scan_started": self.last_scan_started,
            "last_scan_finished": self.last_scan_finished,
            "last_tag_present": self.last_tag is not None,
            "pid": os.getpid(),
            "updated_at": time.time(),
            "payment_supported": False,
            "tag_writes_supported": False,
        }
        _atomic_json(self.state_path, doc)

    def _inventory(self):
        inv = inventory.inventory(self.root)
        inv["service"] = {
            "state": self.state,
            "enabled": self.state in ("READY", "SCANNING", "TAG_PRESENT"),
            "last_error": self.last_error,
            "available": True,
            "pid": os.getpid(),
        }
        inv["last_tag"] = self._public_tag()
        return inv

    def _public_tag(self):
        if not self.last_tag:
            return None
        return {k: v for k, v in self.last_tag.items() if k != "raw"}

    def status(self):
        with self.lock:
            inv = self._inventory()
            inv.update({
                "success": True,
                "schema": STATUS_SCHEMA,
                "state": self.state,
                "supported": bool(inv["vendor_transport_present"]),
                "ready": self.state in ("READY", "TAG_PRESENT"),
                "enabled": self.state in ("READY", "SCANNING", "TAG_PRESENT"),
                "device_open": self.transport.fd >= 0,
                "protocol": abi.PROTOCOL_NAME,
                "protocol_verified": abi.PROTOCOL_VERIFIED,
                "tag_test_supported": bool(inv["vendor_transport_present"]),
                "tag_writes_supported": False,
                "payment": {"supported": False, "note": "no card emulation, payment or eSE support"},
                "mode": "off" if self.state == "OFF" else "reader",
            })
            return inv

    def _ensure_controller(self):
        if self.transport.fd < 0:
            self.transport.open(abi.MODE_FIRMWARE)
        if self.controller is None:
            self.controller = nci.NciController(self.transport)
            try:
                self.controller.reset()
                self.controller.init()
            except Exception:
                self.controller = None
                self.transport.close()
                raise
        return self.controller

    def enable(self):
        with self.lock:
            if self.transport.fd >= 0:
                self.state = "READY"
                self._write_state()
                return self.status()
            self.state = "STARTING"
            self.last_error = None
            self._write_state()
            try:
                self._ensure_controller()
            except TransportError as exc:
                self.state = "ERROR"
                self.last_error = "transport:%s:%s" % (exc.code, exc)
                self._write_state()
                return self._error(exc.code, str(exc))
            except nci.NciError as exc:
                self.state = "ERROR"
                self.last_error = "protocol:%s:%s" % (exc.code, exc)
                self._write_state()
                return self._error(exc.code, str(exc))
            self.state = "READY"
            self._write_state()
            return self.status()

    def disable(self):
        with self.lock:
            self._cancel.set()
            if self.controller is not None:
                try:
                    self.controller.send(nci.command(nci.GID_RF, 0x06, b"\x00"))
                except Exception:
                    pass
            try:
                self.transport.close()
            except Exception:
                pass
            self.controller = None
            self.state = "OFF"
            self._cancel.clear()
            self._write_state()
            return self.status()

    def cancel(self):
        self._cancel.set()
        return {"success": True, "cancelled": True, "state": self.state}

    def _error(self, code, message):
        return {"success": False, "schema": STATUS_SCHEMA, "state": self.state,
                "error": message, "error_code": code, "supported": True,
                "tag_test_supported": False, "uid": None}

    def scan(self, timeout_s=10.0, read_ndef=True):
        timeout_s = max(1.0, min(float(timeout_s), 30.0))
        with self.lock:
            if self.state not in ("READY", "TAG_PRESENT"):
                return self._error("NOT_ENABLED", "NFC is disabled; enable it first")
            if self._cancel.is_set():
                self._cancel.clear()
            ctrl = self.controller
            if ctrl is None:
                return self._error("NOT_INITIALIZED", "controller is not initialized")
            self.state = "SCANNING"
            self.last_scan_started = time.time()
            self._write_state()
            self.last_tag = None
            try:
                ctrl.start_discovery(timeout_s=min(2.0, timeout_s))
                act = ctrl.wait_activation(timeout_s)
                tag = {
                    "schema": "nuxel.nfc-tag/1",
                    "detected_at": time.time(),
                    "technology": "NFC-A",
                    "protocol": act["protocol"],
                    "activation_params_hex": act["activation_params_hex"],
                    "uid": act["activation_params_hex"] or None,
                    "ndef": None,
                    "ndef_error": None,
                }
                if read_ndef:
                    try:
                        msg = nci.read_type2_ndef(ctrl, timeout_s=1.5)
                        parsed = ndef.parse_message(msg)
                        tag["ndef"] = parsed
                    except (nci.NciError, ndef.NdefError) as exc:
                        tag["ndef_error"] = getattr(exc, "code", "NDEF_ERROR") + ": " + str(exc)
                self.last_tag = tag
                self.state = "TAG_PRESENT"
                self.last_scan_finished = time.time()
                self._write_state()
                return {"success": True, "schema": STATUS_SCHEMA, "state": self.state,
                        "tag": self._public_tag(), "tag_test_supported": True,
                        "physical_verified": False,
                        "note": "tag data is ephemeral; no UID/payload was persisted"}
            except nci.NciError as exc:
                self.state = "READY"
                self.last_scan_finished = time.time()
                self.last_error = "%s:%s" % (exc.code, exc)
                self._write_state()
                code = "NO_TAG" if exc.code == "NO_TAG" else exc.code
                return {"success": False, "schema": STATUS_SCHEMA, "state": self.state,
                        "error": str(exc), "error_code": code, "tag": None,
                        "tag_test_supported": True}
            except Exception as exc:
                self.state = "ERROR"
                self.last_scan_finished = time.time()
                self.last_error = "scan:%s" % exc
                self._write_state()
                return self._error("SCAN_FAILED", str(exc))

    def read_last(self):
        with self.lock:
            tag = self._public_tag()
            if not tag:
                return {"success": False, "error": "no tag has been read in this session",
                        "error_code": "NO_TAG"}
            return {"success": True, "tag": tag, "ephemeral": True}

    def clear(self):
        with self.lock:
            self.last_tag = None
            self.state = "READY" if self.transport.fd >= 0 else "OFF"
            self._write_state()
            return {"success": True, "state": self.state}

    def dispatch(self, verb, params=None):
        params = params or {}
        if verb in ("status", "get", "diagnostics"):
            return self.status()
        if verb in ("enable", "set-enabled"):
            return self.enable() if params.get("enabled", True) else self.disable()
        if verb in ("disable", "off"):
            return self.disable()
        if verb == "scan":
            return self.scan(params.get("timeout_s", 10.0),
                             bool(params.get("read_ndef", True)))
        if verb in ("read", "read-tag"):
            return self.read_last()
        if verb == "cancel":
            return self.cancel()
        if verb == "clear":
            return self.clear()
        return {"success": False, "error": "unknown nfc verb", "verb": verb}


def _peer_uid(conn):
    try:
        creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        _pid, uid, _gid = struct.unpack("3i", creds)
        return uid
    except OSError:
        return -1


def serve(socket_path=None):
    socket_path = socket_path or abi.SOCKET_PATH
    os.makedirs(os.path.dirname(socket_path), exist_ok=True)
    try:
        os.unlink(socket_path)
    except OSError:
        pass
    d = NfcDaemon()
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    old = os.umask(0o177)
    try:
        srv.bind(socket_path)
        os.chmod(socket_path, 0o600)
    finally:
        os.umask(old)
    srv.listen(8)
    print("nuxel-nfc ready on %s" % socket_path, flush=True)
    try:
        while True:
            conn, _addr = srv.accept()
            try:
                if _peer_uid(conn) != 0:
                    conn.sendall(b'{"success":false,"error":"permission_denied","error_code":"EPERM"}\n')
                    continue
                raw = b""
                while not raw.endswith(b"\n") and len(raw) <= MAX_REQUEST:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    raw += chunk
                if len(raw) > MAX_REQUEST:
                    conn.sendall(b'{"success":false,"error":"request_too_large","error_code":"EMSGSIZE"}\n')
                    continue
                try:
                    req = json.loads(raw.decode("utf-8"))
                    verb = str(req.get("verb", ""))
                    params = req.get("params") or {}
                    if not isinstance(params, dict):
                        raise ValueError("params must be an object")
                except (ValueError, UnicodeDecodeError) as exc:
                    conn.sendall(json.dumps({"success": False, "error": str(exc),
                                             "error_code": "EBADREQUEST"}).encode() + b"\n")
                    continue
                try:
                    out = d.dispatch(verb, params)
                except Exception as exc:  # noqa: BLE001
                    traceback.print_exc()
                    out = {"success": False, "error": str(exc), "error_code": "EINTERNAL"}
                conn.sendall(json.dumps(out, sort_keys=True).encode() + b"\n")
            finally:
                conn.close()
    finally:
        try:
            d.disable()
        except Exception:
            pass
        srv.close()
        try:
            os.unlink(socket_path)
        except OSError:
            pass


def client(verb, params=None, timeout_s=5.0, socket_path=None):
    socket_path = socket_path or abi.SOCKET_PATH
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout_s)
    try:
        s.connect(socket_path)
        s.sendall((json.dumps({"verb": verb, "params": params or {}}) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        if not buf:
            raise OSError("empty response")
        return json.loads(buf.decode("utf-8"))
    finally:
        s.close()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="nuxel-nfc")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("daemon")
    sub.add_parser("status")
    sub.add_parser("enable")
    sub.add_parser("disable")
    sub.add_parser("read")
    sub.add_parser("inventory")
    p = sub.add_parser("scan")
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--no-ndef", action="store_true")
    p = sub.add_parser("selftest")
    args = ap.parse_args(argv)
    if args.cmd == "daemon":
        serve()
        return 0
    if args.cmd == "inventory":
        print(json.dumps(inventory.inventory(), indent=2, sort_keys=True))
        return 0
    if args.cmd == "selftest":
        # Import-time pure checks only; no hardware is opened.
        assert abi.SEC_NFC_SET_MODE == 0x40045301
        assert nci.command(0, 0, b"\x00").hex() == "20000100"
        msg = bytes([0xD1, 0x01, 0x05]) + b"T" + bytes([0x02]) + b"en" + b"hi"
        assert ndef.parse_message(msg)["records"][0]["preview"] == "hi"
        print("selftest: PASS (ABI, NCI framing, NDEF parser; no hardware opened)")
        return 0
    try:
        if args.cmd in (None, "status"):
            out = client("status")
        elif args.cmd == "enable":
            out = client("enable", {"enabled": True})
        elif args.cmd == "disable":
            out = client("disable")
        elif args.cmd == "scan":
            out = client("scan", {"timeout_s": args.timeout,
                                  "read_ndef": not args.no_ndef},
                         timeout_s=args.timeout + 8)
        elif args.cmd == "read":
            out = client("read")
        else:
            out = {"success": False, "error": "unknown command"}
    except OSError:
        out = inventory.inventory()
        out["service"] = {"available": False, "state": "OFF",
                          "reason": "nuxel-nfcd is not running"}
        out["success"] = True
        out["schema"] = STATUS_SCHEMA
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("success", True) else 1


if __name__ == "__main__":
    sys.exit(main())
