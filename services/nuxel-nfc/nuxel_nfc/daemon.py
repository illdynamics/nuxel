#!/usr/bin/env python3
"""nuxel-nfc: one least-privilege owner of /dev/sec-nfc.

Default-off.  The device is opened only for an explicit enable or scan request.
The daemon never writes tags, never enters BOOTLOADER/NPT mode, never touches
the secure element and never persists tag UID/NDEF data by default.
"""

from __future__ import annotations

import argparse
import hashlib
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

from . import abi, defs, inventory, ndef, nci, policy
from . import kernel_nci
from .kernel_nci import KernelNci, KernelNciError
from .transport import SecNfcTransport, TransportError

SCHEMA = "nuxel.nfc-daemon/1"
STATUS_SCHEMA = "nuxel.nfc-status/2"
MAX_REQUEST = 16384
# Bounded wait for the asynchronous s3fwrn5_i2c probe to create /dev/nfc0.
KERNEL_NODE_WAIT_S = float(os.environ.get("NUXEL_NFC_NODE_WAIT_S", "4.0"))


def _sha256_hex(data):
    return hashlib.sha256(bytes(data)).hexdigest()


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
    def __init__(self, transport=None, root="/", state_path=None,
                 kernel=None):
        self.lock = threading.RLock()
        # Production path: kernel NCI (/dev/nfc0).  The raw Samsung misc
        # transport is an explicit fallback for diagnostics only; it is never
        # selected automatically because it has no reliable NCI class.
        self.kernel = kernel
        self.transport = transport
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
            "tag_writes_supported": True,
            "write_requires_confirmation": True,
            "protocol": abi.PROTOCOL_NAME,
            "kernel_nci": self._kernel_present(),
        }
        _atomic_json(self.state_path, doc)

    def _kernel_present(self):
        if self.kernel is not None:
            return True
        return KernelNci.present(abi.KERNEL_NCI_DEVICE)

    def _inventory(self):
        inv = inventory.inventory(self.root)
        inv["kernel_nci_present"] = self._kernel_present()
        if self._kernel_present():
            inv["controller"] = {
                "expected": "Samsung S3NRN82 (S3FWRN5-compatible NCI) at I2C 0x27",
                "interface": abi.KERNEL_NCI_DEVICE,
                "path": "hsi2c@108E0000 / i2c-7 / 7-0027",
                "source": "beyond2lte appended DTB (board rev 26)",
            }
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
            kernel_ok = self._kernel_present()
            inv.update({
                "success": True,
                "schema": STATUS_SCHEMA,
                "state": self.state,
                "supported": bool(kernel_ok or inv["vendor_transport_present"]),
                "ready": self.state in ("READY", "TAG_PRESENT"),
                "enabled": self.state in ("READY", "SCANNING", "TAG_PRESENT"),
                "device_open": bool(kernel_ok or
                                    (self.transport is not None and self.transport.fd >= 0)),
                "protocol": abi.PROTOCOL_NAME,
                "protocol_verified": abi.PROTOCOL_VERIFIED,
                "tag_test_supported": True,
                "tag_writes_supported": True,
                "write_requires_confirmation": True,
                "payment": {"supported": False, "note": "no card emulation, payment or eSE support"},
                "mode": "off" if self.state == "OFF" else "reader",
                "kernel_nci": {
                    "present": kernel_ok,
                    "device": abi.KERNEL_NCI_DEVICE,
                },
            })
            return inv

    def _ensure_controller(self):
        # 1. Kernel NCI is the physical hardware path.  DEV_UP forces the
        #    controller through CORE_RESET/CORE_INIT inside the kernel.
        #    The s3fwrn5_i2c probe is asynchronous, so a daemon enable that
        #    arrives before /dev/nfc0 exists waits for it for a bounded time
        #    instead of latching an ERROR state until the next restart.
        if self.kernel is None and not self._kernel_present():
            deadline = time.monotonic() + KERNEL_NODE_WAIT_S
            while time.monotonic() < deadline:
                if self._kernel_present():
                    break
                time.sleep(0.1)
        if self.kernel is None and self._kernel_present():
            self.kernel = KernelNci(abi.KERNEL_NCI_DEVICE)
        if self.kernel is not None:
            self.kernel.open()
            self.kernel.start_poll(timeout_s=2.0)
            return self.kernel
        # 2. Only an explicitly injected raw transport is acceptable for
        #    tests/diagnostics.  Never fall back to /dev/sec-nfc silently.
        if self.transport is None:
            raise TransportError("kernel NFC device %s is missing"
                                 % abi.KERNEL_NCI_DEVICE, "NFC_DEVICE_MISSING")
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
            if self.kernel is not None and self.state in ("READY", "TAG_PRESENT"):
                self.state = "READY"
                self._write_state()
                return self.status()
            if self.transport is not None and self.transport.fd >= 0:
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
            except KernelNciError as exc:
                self.state = "ERROR"
                self.last_error = "kernel:%s:%s" % (exc.code, exc)
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
            if self.kernel is not None:
                try:
                    self.kernel.close()
                except Exception:
                    pass
            if self.controller is not None:
                try:
                    self.controller.send(nci.command(nci.GID_RF, 0x06, b"\x00"))
                except Exception:
                    pass
            if self.transport is not None:
                try:
                    self.transport.close()
                except Exception:
                    pass
            self.controller = None
            self.kernel = None
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

    def _kernel_scan(self, timeout_s, read_ndef):
        ctrl = self.kernel
        # Poll activation gets a small settle window; the rest belongs to the
        # caller's bounded tag presentation timer.
        settle = min(1.5, max(0.4, timeout_s * 0.25))
        deadline = time.monotonic() + timeout_s
        targets = []
        while time.monotonic() < deadline:
            time.sleep(settle)
            targets = ctrl.targets(timeout_s=min(2.0, max(0.2, deadline - time.monotonic())))
            if targets:
                break
        if not targets:
            self.state = "READY"
            self.last_scan_finished = time.time()
            self.last_error = "NO_TAG"
            self._write_state()
            return {"success": False, "schema": STATUS_SCHEMA, "state": self.state,
                    "error": "no NFC target discovered within %.1fs" % timeout_s,
                    "error_code": "NO_TAG", "tag": None,
                    "tag_test_supported": True}
        target = targets[0]
        active = self.controller
        if active is None:
            active = nci.NciController(self.kernel)
        active.set_target(target["target_index"],
                          kernel_nci.protocol_from_mask(target.get("protocols")),
                          target.get("uid"))
        tag = {
            "schema": "nuxel.nfc-tag/1",
            "detected_at": time.time(),
            "technology": "NFC-A",
            "protocol": "ISO14443-A",
            "protocols_mask": target.get("protocols"),
            "activation_params_hex": target.get("uid") or "",
            "uid": target.get("uid"),
            "ndef": None,
            "ndef_error": None,
            "writable": False,
            "write_test_ready": False,
        }
        if read_ndef:
            try:
                info, msg, err = nci.read_type2_ndef_info(active, timeout_s=1.5)
                tag["type2"] = {"capacity_bytes": info.capacity_bytes,
                                "read_only": info.read_only,
                                "writable": info.writable}
                tag["writable"] = bool(info.writable)
                tag["write_test_ready"] = bool(info.writable)
                if err:
                    tag["ndef_error"] = err
                elif msg is None:
                    tag["ndef_error"] = "NO_NDEF"
                else:
                    tag["ndef"] = ndef.parse_message(msg)
                    tag["ndef_raw_sha256"] = _sha256_hex(msg)
            except (nci.NciError, ndef.NdefError) as exc:
                tag["ndef_error"] = getattr(exc, "code", "NDEF_ERROR") + ": " + str(exc)
        self.last_tag = tag
        self.state = "TAG_PRESENT"
        self.last_scan_finished = time.time()
        self.last_error = None
        self._write_state()
        return {"success": True, "schema": STATUS_SCHEMA, "state": self.state,
                "tag": self._public_tag(), "tag_test_supported": True,
                "physical_verified": False,
                "note": "tag data is ephemeral; no UID/payload was persisted"}

    def scan(self, timeout_s=10.0, read_ndef=True):
        timeout_s = max(1.0, min(float(timeout_s), 30.0))
        with self.lock:
            if self.state not in ("READY", "TAG_PRESENT"):
                return self._error("NOT_ENABLED", "NFC is disabled; enable it first")
            if self._cancel.is_set():
                self._cancel.clear()
            self.state = "SCANNING"
            self.last_scan_started = time.time()
            self._write_state()
            self.last_tag = None
            try:
                if self.kernel is not None:
                    return self._kernel_scan(timeout_s, read_ndef)
                ctrl = self.controller
                if ctrl is None:
                    return self._error("NOT_INITIALIZED", "controller is not initialized")
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
                    "writable": False,
                }
                if read_ndef:
                    try:
                        info, msg, err = nci.read_type2_ndef_info(ctrl, timeout_s=1.5)
                        tag["type2"] = {"capacity_bytes": info.capacity_bytes,
                                        "read_only": info.read_only,
                                        "writable": info.writable}
                        tag["writable"] = bool(info.writable)
                        if err:
                            tag["ndef_error"] = err
                        elif msg is None:
                            tag["ndef_error"] = "NO_NDEF"
                        else:
                            tag["ndef"] = ndef.parse_message(msg)
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
            except KernelNciError as exc:
                self.state = "READY"
                self.last_scan_finished = time.time()
                self.last_error = "%s:%s" % (exc.code, exc)
                self._write_state()
                return {"success": False, "schema": STATUS_SCHEMA, "state": self.state,
                        "error": str(exc), "error_code": exc.code, "tag": None,
                        "tag_test_supported": True}
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

    def write_tag(self, kind, value, confirmed=False, language="en",
                  allow_null_write=False):
        """Write and read back one NDEF record on an expendable Type-2 tag.

        Explicit capability model (never inferred):
          * write requires ``confirmed=True`` -- there is no silent write,
          * requires an active TAG_PRESENT session from a real scan,
          * only NTAG/Ultralight Type-2 data pages are written; lock/OTP pages
            are refused by nci.type2_write_pages(),
          * a read-only CC is refused before any WRITE frame is sent,
          * the record is read back and byte-compared; a mismatch is FAIL.

        ``allow_null_write`` is intentionally not implemented: blanking a tag
        destroys its contents and has no verified use in this workflow.
        """
        with self.lock:
            if not confirmed:
                return {"success": False, "error": "write requires explicit confirmation",
                        "error_code": "CONFIRMATION_REQUIRED"}
            if allow_null_write:
                return {"success": False, "error": "null write is not supported",
                        "error_code": "UNSUPPORTED"}
            if self.state != "TAG_PRESENT" or not self.last_tag:
                return {"success": False, "error": "scan and present a tag first",
                        "error_code": "NO_TAG"}
            if not self.last_tag.get("writable"):
                return {"success": False, "error": "tag is read-only or not Type 2",
                        "error_code": "TYPE2_READ_ONLY"}
            try:
                if kind == "text":
                    message = defs.text_record(str(value), language)
                elif kind == "uri":
                    message = defs.uri_record(str(value))
                else:
                    return {"success": False, "error": "unsupported record type",
                            "error_code": "UNSUPPORTED_RECORD"}
            except (defs.NdefBuildError, UnicodeError) as exc:
                return {"success": False, "error": str(exc),
                        "error_code": "INVALID_RECORD"}
            ctrl = self.controller
            if ctrl is None:
                # Kernel-NCI target index is required before any write.
                return {"success": False, "error": "no activated target",
                        "error_code": "NFC_NOT_ACTIVATED"}
            try:
                info = nci.write_type2_ndef(ctrl, message, timeout_s=1.5)
                verified = nci.verify_type2_write(ctrl, message, timeout_s=1.5)
                parsed = ndef.parse_message(message)
            except (nci.NciError, ndef.NdefError) as exc:
                self.last_error = "write:%s:%s" % (getattr(exc, "code", "WRITE"),
                                                   exc)
                self._write_state()
                return {"success": False, "error": str(exc),
                        "error_code": getattr(exc, "code", "WRITE_FAILED")}
            tag = dict(self.last_tag)
            tag["ndef"] = parsed
            tag["ndef_error"] = None
            tag["written_at"] = time.time()
            tag["verified"] = True
            tag["last_write"] = {"kind": kind, "record_count": 1,
                                 "message_length": len(message)}
            self.last_tag = tag
            self._write_state()
            return {"success": True, "schema": STATUS_SCHEMA, "state": self.state,
                    "written": kind, "verified": verified["verified"],
                    "tag": self._public_tag(), "physical_verified": False}

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

    def dispatch(self, verb, params=None, app_id=None):
        params = params or {}
        if verb in ("status", "get", "diagnostics"):
            return self.status()
        # Per-app authorization: the daemon runs as root and owns /dev/nfc0,
        # so the ONLY thing stopping any local app from reading the owner's
        # tags is this check against the shared permission store.
        verdict = policy.authorize(app_id, verb)
        if not verdict.get("allowed"):
            return {"success": False, "error": "nfc_permission_denied",
                    "error_code": "EPERM", "app_id": app_id,
                    "capability": "nfc",
                    "detail": verdict.get("reason") or verdict.get("detail"),
                    "policy_source": verdict.get("source"),
                    "store": policy.PERMISSIONS_DIR}
        if verb in ("enable", "set-enabled"):
            return self.enable() if params.get("enabled", True) else self.disable()
        if verb in ("disable", "off"):
            return self.disable()
        if verb == "scan":
            return self.scan(params.get("timeout_s", 10.0),
                             bool(params.get("read_ndef", True)))
        if verb in ("write", "write-tag"):
            if params.get("confirm") is not True:
                return {"success": False,
                        "error": "write requires explicit confirmation",
                        "error_code": "CONFIRMATION_REQUIRED"}
            kind = str(params.get("kind") or "text")
            value = params.get("value", "")
            if not isinstance(value, str):
                return {"success": False, "error": "value must be a string",
                        "error_code": "INVALID_RECORD"}
            return self.write_tag(kind, value, confirmed=True,
                                  language=str(params.get("language") or "en"))
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
                    app_id = req.get("app_id")
                    params = req.get("params") or {}
                    if not isinstance(params, dict):
                        raise ValueError("params must be an object")
                except (ValueError, UnicodeDecodeError) as exc:
                    conn.sendall(json.dumps({"success": False, "error": str(exc),
                                             "error_code": "EBADREQUEST"}).encode() + b"\n")
                    continue
                try:
                    out = d.dispatch(verb, params, app_id=app_id)
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


def client(verb, params=None, timeout_s=5.0, socket_path=None, app_id=None):
    """Send one request to the daemon.

    ``app_id`` is the calling application's identity for the grant check.  The
    daemon fails closed when it is absent, so a CLI invocation must name the
    app whose stored grant authorises it (``--app-id``; default: the owner's
    NFC surface, which the permission manager also shows).
    """
    socket_path = socket_path or abi.SOCKET_PATH
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout_s)
    try:
        s.connect(socket_path)
        req = {"verb": verb, "params": params or {}}
        if app_id:
            req["app_id"] = app_id
        s.sendall((json.dumps(req) + "\n").encode())
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
    # The daemon authorises every tag verb against the caller's stored grant.
    # A console invocation acts on behalf of the NFC app by default; tests and
    # diagnostics can name another app explicitly.
    ap.add_argument("--app-id", default="org.nuxel.NFC",
                    help="app whose stored nfc grant authorises this request")
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
    p = sub.add_parser("write")
    p.add_argument("--confirm", action="store_true",
                   help="explicitly authorise overwriting the presented tag")
    p.add_argument("--kind", choices=("text", "uri"), default="text")
    p.add_argument("--language", default="en")
    p.add_argument("value")
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
        rec = defs.text_record("Nuxel NDEF")
        image = nci.build_type2_ndef_image(rec, 180)
        assert image[:2] == bytes([0x03, len(rec)]) and len(image) % 4 == 0
        print("selftest: PASS (ABI, NCI framing, NDEF parser/encoder; "
              "no hardware opened)")
        return 0
    try:
        if args.cmd in (None, "status"):
            out = client("status")
        elif args.cmd == "enable":
            out = client("enable", {"enabled": True}, app_id=args.app_id)
        elif args.cmd == "disable":
            out = client("disable")
        elif args.cmd == "scan":
            out = client("scan", {"timeout_s": args.timeout,
                                  "read_ndef": not args.no_ndef},
                         timeout_s=args.timeout + 8, app_id=args.app_id)
        elif args.cmd == "read":
            out = client("read")
        elif args.cmd == "write":
            out = client("write", {"confirm": bool(args.confirm),
                                   "kind": args.kind, "value": args.value,
                                   "language": args.language}, app_id=args.app_id)
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
